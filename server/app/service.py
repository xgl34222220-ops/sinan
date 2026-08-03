from __future__ import annotations

import json
import time
from typing import Any

from . import ai
from .config import settings
from .db import database
from .lottery import lottery_client
from .models import LOTTERIES, SnapshotModel
from .predictor import predict


SERVICE_VERSION = "1.0.0"


def run_lottery_cycle(lottery_key: str) -> dict[str, Any]:
    spec = LOTTERIES.get(lottery_key)
    if spec is None:
        raise KeyError(f"未知彩种：{lottery_key}")

    existing_count = len(database.list_draws(lottery_key, 180))
    sync_days = settings.history_days if existing_count < 180 else 2
    draws, next_period, server_time, next_draw_at = lottery_client.fetch_recent(
        spec,
        sync_days,
    )
    database.save_draws(draws)
    settled = database.settle_forecasts(lottery_key)
    history = database.list_draws(lottery_key, spec.history_target)
    latest = history[-1]

    generated: list[str] = []
    if next_period and next_period != "待同步" and database.get_draw(lottery_key, next_period) is None:
        native_model = "tianji-native-cloud-v1"
        if not database.has_forecast(lottery_key, next_period, "native", native_model):
            native = predict(history)
            selected = native.selected
            inserted = database.save_forecast(
                lottery=lottery_key,
                target_period=next_period,
                trained_through_period=latest.period,
                position=selected.position,
                top6=selected.top6,
                top7=selected.top7,
                probabilities=selected.probabilities,
                source="native",
                model=native_model,
                analysis=native.analysis,
                risk_note=native.risk_note,
            )
            if inserted is not None:
                generated.append("native")

        if settings.ai_enabled and not database.has_forecast(
            lottery_key,
            next_period,
            "ai",
            settings.ai_model,
        ):
            try:
                result = ai.analyze(history, next_period)
                inserted = database.save_forecast(
                    lottery=lottery_key,
                    target_period=next_period,
                    trained_through_period=latest.period,
                    position=result.position,
                    top6=result.top6,
                    top7=result.top7,
                    probabilities=result.probabilities,
                    source="ai",
                    model=result.model,
                    analysis=f"{result.analysis} · 云端耗时 {result.latency_ms / 1000:.1f}s",
                    risk_note=result.risk_note,
                )
                if inserted is not None:
                    generated.append("ai")
            except Exception as exc:
                database.set_state(
                    f"ai_error:{lottery_key}",
                    json.dumps(
                        {
                            "message": str(exc)[:500],
                            "target_period": next_period,
                            "at": int(time.time() * 1000),
                        },
                        ensure_ascii=False,
                    ),
                )

    result = {
        "lottery": lottery_key,
        "latest_period": latest.period,
        "next_period": next_period,
        "draws": len(history),
        "sync_days": sync_days,
        "settled": settled,
        "generated": generated,
        "server_time_epoch_ms": server_time,
        "next_draw_at_epoch_ms": next_draw_at,
        "completed_at_epoch_ms": int(time.time() * 1000),
    }
    database.set_state(f"cycle:{lottery_key}", json.dumps(result, ensure_ascii=False))
    return result


def run_all_cycles() -> dict[str, Any]:
    started = int(time.time() * 1000)
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for lottery_key in LOTTERIES:
        try:
            results[lottery_key] = run_lottery_cycle(lottery_key)
        except Exception as exc:
            errors[lottery_key] = str(exc)[:500]
    heartbeat = {
        "started_at_epoch_ms": started,
        "completed_at_epoch_ms": int(time.time() * 1000),
        "results": results,
        "errors": errors,
    }
    database.set_state("worker_heartbeat", json.dumps(heartbeat, ensure_ascii=False))
    return heartbeat


def snapshot(lottery_key: str, draw_limit: int = 240) -> SnapshotModel:
    spec = LOTTERIES.get(lottery_key)
    if spec is None:
        raise KeyError(f"未知彩种：{lottery_key}")
    draws = database.list_draws(lottery_key, draw_limit)
    if not draws:
        raise RuntimeError("服务器尚未同步到开奖历史")
    latest = draws[-1]
    cycle = database.get_state(f"cycle:{lottery_key}")
    next_period = "待同步"
    synced_at = int(time.time() * 1000)
    if cycle is not None:
        try:
            value = json.loads(cycle[0])
            next_period = str(value.get("next_period") or "待同步")
            synced_at = int(value.get("completed_at_epoch_ms") or cycle[1])
        except (ValueError, TypeError, json.JSONDecodeError):
            synced_at = cycle[1]
    return SnapshotModel(
        lottery=lottery_key,
        latest=latest,
        next_period=next_period,
        draws=draws,
        forecasts=database.latest_forecasts(lottery_key),
        synced_at_epoch_ms=synced_at,
    )
