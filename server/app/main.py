from __future__ import annotations

import hmac
import json
import time
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse

from .config import settings
from .db import database
from .models import ForecastModel, HealthModel, LOTTERIES, SnapshotModel
from .service import SERVICE_VERSION, run_all_cycles, snapshot


app = FastAPI(
    title="天机云端服务",
    description="全天开奖同步、前向预测冻结与目标期验证",
    version=SERVICE_VERSION,
    docs_url="/docs",
    redoc_url=None,
)


def require_admin(authorization: Annotated[str | None, Header()] = None) -> None:
    expected = settings.api_token
    if not expected:
        raise HTTPException(status_code=503, detail="服务器尚未配置管理令牌")
    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="管理令牌无效")


@app.get("/health", response_model=HealthModel)
def health() -> HealthModel:
    heartbeat = database.get_state("worker_heartbeat")
    heartbeat_at = heartbeat[1] if heartbeat else None
    fresh = bool(
        heartbeat_at
        and int(time.time() * 1000) - heartbeat_at <= max(180_000, settings.poll_seconds * 4_000)
    )
    return HealthModel(
        status="ok" if database.ping() else "degraded",
        database="ok" if database.ping() else "error",
        worker="ok" if fresh else "waiting",
        ai_enabled=settings.ai_enabled,
        version=SERVICE_VERSION,
        last_worker_heartbeat_epoch_ms=heartbeat_at,
    )


@app.get("/v1/lotteries")
def lotteries() -> list[dict[str, object]]:
    return [
        {
            "key": spec.key,
            "name": spec.name,
            "lot_code": spec.lot_code,
            "interval_minutes": spec.interval_minutes,
        }
        for spec in LOTTERIES.values()
    ]


@app.get("/v1/snapshot/{lottery_key}", response_model=SnapshotModel)
def get_snapshot(
    lottery_key: str,
    draw_limit: int = Query(default=240, ge=30, le=1000),
) -> SnapshotModel:
    try:
        return snapshot(lottery_key, draw_limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/v1/forecasts/{lottery_key}", response_model=list[ForecastModel])
def forecasts(
    lottery_key: str,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ForecastModel]:
    if lottery_key not in LOTTERIES:
        raise HTTPException(status_code=404, detail="未知彩种")
    return database.list_forecasts(lottery_key, limit)


@app.post("/v1/admin/run", dependencies=[Depends(require_admin)])
def run_now() -> dict[str, object]:
    return run_all_cycles()


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    cards: list[str] = []
    for key, spec in LOTTERIES.items():
        latest = database.latest_draw(key)
        records = database.latest_forecasts(key)
        if latest is None:
            body = "<p>等待首次同步</p>"
        else:
            forecast_html = "".join(
                f"<li><b>{'AI' if item.source == 'ai' else '本机云端'}</b> "
                f"第 {item.position + 1} 名 · 六码 {' '.join(map(str, item.top6))} "
                f"· 目标期 {item.target_period}</li>"
                for item in records
            ) or "<li>等待生成预测</li>"
            body = (
                f"<p>最新期：<b>{latest.period}</b> · 开奖 {' '.join(map(str, latest.numbers))}</p>"
                f"<ul>{forecast_html}</ul>"
            )
        cards.append(f"<section><h2>{spec.name}</h2>{body}</section>")
    ai_label = "已启用" if settings.ai_enabled else "未配置（仍运行本机云端模型）"
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>天机云端</title><style>
body{{font-family:system-ui,-apple-system,sans-serif;background:#f5f7fb;color:#172033;margin:0;padding:24px}}
main{{max-width:860px;margin:auto}}header,section{{background:white;border-radius:20px;padding:20px;margin-bottom:16px;box-shadow:0 8px 32px #14213d12}}
h1{{margin:0 0 8px}}h2{{margin-top:0}}li{{margin:8px 0;line-height:1.55}}code{{background:#eef3ff;padding:3px 7px;border-radius:7px}}
.small{{color:#65728a;font-size:14px}}</style></head>
<body><main><header><h1>天机云端服务</h1><div class="small">版本 {SERVICE_VERSION} · AI {ai_label} · <a href="/docs">API 文档</a></div></header>
{''.join(cards)}
<section class="small">随机开奖不可可靠预测。本服务只进行统计实验、首次结果冻结和真实目标期验证，不承诺盈利或必中。</section>
</main></body></html>"""
