from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import threading
import time
from typing import Any

from . import ai
from .config import settings
from .db import database
from .lottery import lottery_client
from .models import LOTTERIES, LotterySpec, SnapshotModel
from .predictor import predict
from .runtime_config import RuntimeAiConfig, load_ai_config


SERVICE_VERSION = "1.2.0"
SAFETY_WINDOW_MS = 5_000
_AI_EXECUTOR = ThreadPoolExecutor(max_workers=max(1, len(LOTTERIES)), thread_name_prefix="tianji-ai")
_AI_LOCK = threading.Lock()
_AI_INFLIGHT: set[tuple[str, str, str]] = set()


def _state(key: str, value: dict[str, Any]) -> None:
    database.set_state(key, json.dumps(value, ensure_ascii=False))


def _target_is_open(spec: LotterySpec, trained_through_period: str, target_period: str) -> bool:
    latest, current_next_period, _, next_draw_at = lottery_client.fetch_latest(spec)
    if latest.period != trained_through_period or current_next_period != target_period:
        return False
    if next_draw_at is not None and int(time.time() * 1000) >= next_draw_at - SAFETY_WINDOW_MS:
        return False
    return database.get_draw(spec.key, target_period) is None


def _run_ai_prediction(
    spec: LotterySpec,
    history: list,
    target_period: str,
    trained_through_period: str,
    ai_config: RuntimeAiConfig,
) -> None:
    key = (spec.key, target_period, ai_config.model)
    started = int(time.time() * 1000)
    try:
        _state(
            f"ai_job:{spec.key}",
            {
                "status": "running",
                "target_period": target_period,
                "model": ai_config.model,
                "started_at_epoch_ms": started,
            },
        )
        result = ai.analyze(history, target_period, ai_config)
        if not _target_is_open(spec, trained_through_period, target_period):
            _state(
                f"ai_job:{spec.key}",
                {
                    "status": "discarded",
                    "target_period": target_period,
                    "model": ai_config.model,
                    "message": "AI 完成时目标期已经封盘，结果未写入前向档案",
                    "started_at_epoch_ms": started,
                    "completed_at_epoch_ms": int(time.time() * 1000),
                },
            )
            return
        inserted = database.save_forecast(
            lottery=spec.key,
            target_period=target_period,
            trained_through_period=trained_through_period,
            position=result.position,
            top6=result.top6,
            top7=result.top7,
            probabilities=result.probabilities,
            source="ai",
            model=result.model,
            analysis=f"{result.analysis} · 云端耗时 {result.latency_ms / 1000:.1f}s",
            risk_note=result.risk_note,
        )
        _state(
            f"ai_job:{spec.key}",
            {
                "status": "completed" if inserted is not None else "duplicate",
                "target_period": target_period,
                "model": ai_config.model,
                "latency_ms": result.latency_ms,
                "started_at_epoch_ms": started,
                "completed_at_epoch_ms": int(time.time() * 1000),
            },
        )
    except Exception as exc:
        error = {
            "status": "error",
            "message": str(exc)[:500],
            "target_period": target_period,
            "model": ai_config.model,
            "started_at_epoch_ms": started,
            "completed_at_epoch_ms": int(time.time() * 1000),
        }
        _state(f"ai_job:{spec.key}", error)
        _state(f"ai_error:{spec.key}", error)
    finally:
        with _AI_LOCK:
            _AI_INFLIGHT.discard(key)


def _schedule_ai_prediction(
    spec: LotterySpec,
    history: list,
    target_period: str,
    trained_through_period: str,
    ai_config: RuntimeAiConfig,
) -> bool:
    key = (spec.key, target_period, ai_config.model)
    with _AI_LOCK:
        if key in _AI_INFLIGHT:
            return False
        _AI_INFLIGHT.add(key)
    _state(
        f"ai_job:{spec.key}",
        {
            "status": "queued",
            "target_period": target_period,
            "model": ai_config.model,
            "queued_at_epoch_ms": int(time.time() * 1000),
        },
    )
    _AI_EXECUTOR.submit(
        _run_ai_prediction,
        spec,
        list(history),
        target_period,
        trained_through_period,
        ai_config,
    )
    return True


def run_lottery_cycle(lottery_key: str) -> dict[str, Any]:
    spec = LOTTERIES.get(lottery_key)
    if spec is None:
        raise KeyError(f"未知彩种：{lottery_key}")

    existing_count = len(database.list_draws(lottery_key, 180))
    sync_days = settings.history_days if existing_count < 180 else 2
    draws, next_period, server_time, next_draw_at = lottery_client.fetch_recent(spec, sync_days)
    database.save_draws(draws)

    # 结算必须先于任何预测和 AI 调用；即使模型失败，也不能阻塞已开奖档案更新。
    settled = database.settle_forecasts(lottery_key)
    history = database.list_draws(lottery_key, spec.history_target)
    latest = history[-1]

    generated: list[str] = []
    scheduled: list[str] = []
    errors: dict[str, str] = {}
    now_ms = int(time.time() * 1000)
    before_safety_window = next_draw_at is None or now_ms < next_draw_at - SAFETY_WINDOW_MS
    target_candidate = bool(
        next_period
        and next_period != "待同步"
        and before_safety_window
        and database.get_draw(lottery_key, next_period) is None
    )

    # 先落盘同步状态，避免预测过程异常时页面仍显示上一次旧期号。
    base_result: dict[str, Any] = {
        "lottery": lottery_key,
        "latest_period": latest.period,
        "next_period": next_period,
        "draws": len(history),
        "sync_days": sync_days,
        "settled": settled,
        "generated": generated,
        "scheduled": scheduled,
        "errors": errors,
        "ai_model": load_ai_config().model,
        "server_time_epoch_ms": server_time,
        "next_draw_at_epoch_ms": next_draw_at,
        "completed_at_epoch_ms": int(time.time() * 1000),
    }
    _state(f"cycle:{lottery_key}", base_result)

    if target_candidate:
        native_model = "tianji-native-cloud-v1"
        if not database.has_forecast(lottery_key, next_period, "native", native_model):
            try:
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
            except Exception as exc:
                errors["native"] = str(exc)[:500]
                _state(
                    f"native_error:{lottery_key}",
                    {
                        "message": errors["native"],
                        "target_period": next_period,
                        "at": int(time.time() * 1000),
                    },
                )

        ai_config = load_ai_config()
        if ai_config.complete and not database.has_forecast(
            lottery_key,
            next_period,
            "ai",
            ai_config.model,
        ):
            if _schedule_ai_prediction(spec, history, next_period, latest.period, ai_config):
                scheduled.append("ai")

    base_result.update(
        {
            "generated": generated,
            "scheduled": scheduled,
            "errors": errors,
            "completed_at_epoch_ms": int(time.time() * 1000),
        }
    )
    _state(f"cycle:{lottery_key}", base_result)
    return base_result


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
    _state("worker_heartbeat", heartbeat)
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
