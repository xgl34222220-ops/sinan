from __future__ import annotations

import hmac
import json
import time
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import ai
from .admin_auth import (
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    admin_password_configured,
    change_admin_password,
    create_session,
    verify_admin_password,
    verify_session,
)
from .config import settings
from .db import database
from .models import ForecastModel, HealthModel, LOTTERIES, SnapshotModel
from .runtime_config import RuntimeAiConfig, load_ai_config, save_ai_config
from .service import SERVICE_VERSION, run_all_cycles, snapshot
from .web_ui import admin_page, login_page, public_page


app = FastAPI(
    title="天机云端服务",
    description="全天开奖同步、前向预测冻结、目标期验证与可视化管理",
    version=SERVICE_VERSION,
    docs_url="/docs",
    redoc_url=None,
)


class LoginPayload(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class AiConfigPayload(BaseModel):
    enabled: bool = True
    endpoint: str = Field(default="", max_length=500)
    model: str = Field(default="", max_length=200)
    api_key: str | None = Field(default=None, max_length=1000)
    timeout_seconds: int = Field(default=120, ge=20, le=300)


class PasswordPayload(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


def require_admin_token(authorization: Annotated[str | None, Header()] = None) -> None:
    expected = settings.api_token
    if not expected:
        raise HTTPException(status_code=503, detail="服务器尚未配置管理令牌")
    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="管理令牌无效")


def require_admin_session(request: Request) -> None:
    if not verify_session(request.cookies.get(SESSION_COOKIE)):
        raise HTTPException(status_code=401, detail="登录已过期")


def require_admin_action(
    request: Request,
    marker: Annotated[str | None, Header(alias="X-Tianji-Admin")] = None,
) -> None:
    require_admin_session(request)
    if marker != "1":
        raise HTTPException(status_code=400, detail="缺少控制台请求标记")


def health_value() -> HealthModel:
    heartbeat = database.get_state("worker_heartbeat")
    heartbeat_at = heartbeat[1] if heartbeat else None
    fresh = bool(
        heartbeat_at
        and int(time.time() * 1000) - heartbeat_at <= max(180_000, settings.poll_seconds * 4_000)
    )
    runtime_ai = load_ai_config()
    database_ok = database.ping()
    return HealthModel(
        status="ok" if database_ok else "degraded",
        database="ok" if database_ok else "error",
        worker="ok" if fresh else "waiting",
        ai_enabled=runtime_ai.complete,
        version=SERVICE_VERSION,
        last_worker_heartbeat_epoch_ms=heartbeat_at,
    )


def _decode_state(key: str) -> dict[str, Any] | None:
    value = database.get_state(key)
    if value is None:
        return None
    try:
        decoded = json.loads(value[0])
        return decoded if isinstance(decoded, dict) else {"value": decoded, "updated_at_epoch_ms": value[1]}
    except json.JSONDecodeError:
        return {"value": value[0], "updated_at_epoch_ms": value[1]}


def _lottery_overview(key: str) -> dict[str, Any]:
    spec = LOTTERIES[key]
    latest = database.latest_draw(key)
    cycle = _decode_state(f"cycle:{key}") or {}
    records = database.latest_forecasts(key)
    return {
        "key": key,
        "name": spec.name,
        "latest_period": latest.period if latest else None,
        "numbers": latest.numbers if latest else [],
        "next_period": cycle.get("next_period", "待同步"),
        "synced_at_epoch_ms": cycle.get("completed_at_epoch_ms"),
        "draw_count": len(database.list_draws(key, spec.history_target)),
        "forecasts": [record.model_dump() for record in records],
    }


def _records_overview(limit_each: int = 80) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, spec in LOTTERIES.items():
        for record in database.list_forecasts(key, limit_each):
            value = record.model_dump()
            value["lottery_name"] = spec.name
            rows.append(value)
    return sorted(rows, key=lambda item: int(item["created_at_epoch_ms"]), reverse=True)[:120]


def _config_from_payload(payload: AiConfigPayload) -> RuntimeAiConfig:
    current = load_ai_config()
    return RuntimeAiConfig(
        enabled=payload.enabled,
        endpoint=payload.endpoint.strip().rstrip("/"),
        model=payload.model.strip(),
        api_key=current.api_key if payload.api_key is None else payload.api_key.strip(),
        timeout_seconds=payload.timeout_seconds,
        updated_at_epoch_ms=current.updated_at_epoch_ms,
    )


@app.get("/health", response_model=HealthModel)
def health() -> HealthModel:
    return health_value()


@app.get("/v1/public/overview")
def public_overview() -> dict[str, Any]:
    runtime_ai = load_ai_config()
    return {
        "health": health_value().model_dump(),
        "ai": runtime_ai.public_dict(),
        "lotteries": [_lottery_overview(key) for key in LOTTERIES],
    }


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


@app.post("/v1/admin/run", dependencies=[Depends(require_admin_token)])
def run_now_legacy() -> dict[str, object]:
    return run_all_cycles()


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return public_page()


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request) -> str:
    if verify_session(request.cookies.get(SESSION_COOKIE)):
        return admin_page()
    return login_page(admin_password_configured())


@app.post("/admin/api/login")
def admin_login(payload: LoginPayload, response: Response) -> dict[str, bool]:
    if not admin_password_configured():
        raise HTTPException(status_code=503, detail="尚未设置管理密码，请先运行服务器更新脚本")
    if not verify_admin_password(payload.password):
        time.sleep(0.35)
        raise HTTPException(status_code=401, detail="管理密码不正确")
    response.set_cookie(
        SESSION_COOKIE,
        create_session(),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return {"ok": True}


@app.post("/admin/api/logout", dependencies=[Depends(require_admin_action)])
def admin_logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/admin/api/state", dependencies=[Depends(require_admin_session)])
def admin_state() -> dict[str, Any]:
    runtime_ai = load_ai_config()
    errors = {
        key: _decode_state(f"ai_error:{key}")
        for key in LOTTERIES
        if database.get_state(f"ai_error:{key}") is not None
    }
    return {
        "health": health_value().model_dump(),
        "ai": runtime_ai.public_dict(),
        "heartbeat": _decode_state("worker_heartbeat"),
        "ai_errors": errors,
        "lotteries": [_lottery_overview(key) for key in LOTTERIES],
        "records": _records_overview(),
    }


@app.put("/admin/api/ai", dependencies=[Depends(require_admin_action)])
def update_ai(payload: AiConfigPayload) -> dict[str, object]:
    try:
        config = save_ai_config(
            enabled=payload.enabled,
            endpoint=payload.endpoint,
            model=payload.model,
            api_key=payload.api_key,
            timeout_seconds=payload.timeout_seconds,
        )
        return config.public_dict()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/admin/api/ai/test", dependencies=[Depends(require_admin_action)])
def test_ai(payload: AiConfigPayload) -> dict[str, object]:
    try:
        result = ai.test_connection(_config_from_payload(payload))
        return {
            "ok": True,
            "message": result.message,
            "latency_ms": result.latency_ms,
            "models": result.models,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"连接测试失败：{str(exc)[:300]}") from exc


@app.post("/admin/api/ai/models", dependencies=[Depends(require_admin_action)])
def list_ai_models(payload: AiConfigPayload) -> dict[str, object]:
    try:
        result = ai.discover_models(_config_from_payload(payload))
        return {
            "ok": True,
            "message": result.message,
            "latency_ms": result.latency_ms,
            "models": result.models,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"读取模型失败：{str(exc)[:300]}") from exc


@app.post("/admin/api/run", dependencies=[Depends(require_admin_action)])
def admin_run(background_tasks: BackgroundTasks) -> dict[str, object]:
    background_tasks.add_task(run_all_cycles)
    return {"accepted": True, "message": "后台任务已开始"}


@app.put("/admin/api/password", dependencies=[Depends(require_admin_action)])
def update_password(payload: PasswordPayload) -> dict[str, bool]:
    if not verify_admin_password(payload.current_password):
        raise HTTPException(status_code=401, detail="当前管理密码不正确")
    try:
        change_admin_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}
