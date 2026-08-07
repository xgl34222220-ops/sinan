from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import json
import time
from typing import Any, Iterator

from . import ai, push_alerts, telegram_events
from .config import settings
from .db import database
from .lottery import lottery_client
from .models import LOTTERIES, LotterySpec, SnapshotModel
from .predictor import predict
from .runtime_config import RuntimeAiConfig, load_ai_config


SERVICE_VERSION = "1.8.0"
SAFETY_WINDOW_MS = 5_000
AI_RETRY_AFTER_MS = 30_000
_AI_EXECUTOR = ThreadPoolExecutor(
    max_workers=max(2, len(LOTTERIES)),
    thread_name_prefix="tianji-ai",
)


def _state(key: str, value: dict[str, Any]) -> None:
    database.set_state(key, json.dumps(value, ensure_ascii=False))


@contextmanager
def _record_stage(stages: list[dict[str, Any]], name: str) -> Iterator[None]:
    started = time.monotonic()
    started_at = int(time.time() * 1000)
    entry: dict[str, Any] = {
        "name": name,
        "status": "running",
        "started_at_epoch_ms": started_at,
    }
    stages.append(entry)
    try:
        yield
        entry["status"] = "ok"
    except Exception as exc:
        entry["status"] = "error"
        entry["message"] = str(exc)[:500]
        raise
    finally:
        entry["completed_at_epoch_ms"] = int(time.time() * 1000)
        entry["duration_ms"] = round((time.monotonic() - started) * 1000, 1)


def _ai_job_state(
    spec: LotterySpec,
    *,
    status: str,
    target_period: str,
    model: str,
    message: str = "",
    started_at_epoch_ms: int | None = None,
    latency_ms: int | None = None,
) -> None:
    now = int(time.time() * 1000)
    payload: dict[str, Any] = {
        "status": status,
        "target_period": target_period,
        "model": model,
        "message": message[:500],
        "updated_at_epoch_ms": now,
    }
    if started_at_epoch_ms is not None:
        payload["started_at_epoch_ms"] = started_at_epoch_ms
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    if status == "queued":
        payload["queued_at_epoch_ms"] = now
    if status in {"completed", "duplicate", "discarded", "error"}:
        payload["completed_at_epoch_ms"] = now
    _state(f"ai_job:{spec.key}", payload)


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
    started = int(time.time() * 1000)
    database.finish_forecast_job(
        lottery=spec.key,
        target_period=target_period,
        source="ai",
        status="running",
        model=ai_config.model,
    )
    _ai_job_state(
        spec,
        status="running",
        target_period=target_period,
        model=ai_config.model,
        started_at_epoch_ms=started,
    )
    try:
        recent_ai_positions = [
            forecast.position
            for forecast in database.list_forecasts(spec.key, 20)
            if forecast.source == "ai"
        ][:12]
        strategy_weights = database.get_strategy_weights(spec.key, "ai")
        result = ai.analyze(
            history,
            target_period,
            ai_config,
            recent_positions=recent_ai_positions,
            strategy_weights=strategy_weights,
        )
        database.save_ai_usage(
            lottery=spec.key,
            target_period=target_period,
            model=ai_config.model,
            request_count=result.request_count,
            prompt_tokens=result.prompt_tokens,
            prompt_cache_hit_tokens=result.prompt_cache_hit_tokens,
            prompt_cache_miss_tokens=result.prompt_cache_miss_tokens,
            completion_tokens=result.completion_tokens,
            reasoning_tokens=result.reasoning_tokens,
            cache_hit_rate=result.cache_hit_rate,
        )
        _state(
            f"ai_usage:{spec.key}",
            {
                "target_period": target_period,
                "model": ai_config.model,
                "request_count": result.request_count,
                "prompt_tokens": result.prompt_tokens,
                "prompt_cache_hit_tokens": result.prompt_cache_hit_tokens,
                "prompt_cache_miss_tokens": result.prompt_cache_miss_tokens,
                "completion_tokens": result.completion_tokens,
                "reasoning_tokens": result.reasoning_tokens,
                "cache_hit_rate": result.cache_hit_rate,
                "updated_at_epoch_ms": int(time.time() * 1000),
            },
        )
        if not _target_is_open(spec, trained_through_period, target_period):
            message = "AI 完成时目标期已经封盘，结果未写入前向档案"
            database.finish_forecast_job(
                lottery=spec.key,
                target_period=target_period,
                source="ai",
                status="discarded",
                message=message,
                model=ai_config.model,
            )
            _ai_job_state(
                spec,
                status="discarded",
                target_period=target_period,
                model=ai_config.model,
                message=message,
                started_at_epoch_ms=started,
                latency_ms=result.latency_ms,
            )
            return

        inserted = database.save_forecast_with_strategies(
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
            probabilities_by_strategy=result.strategy_probabilities,
            weights=result.strategy_weights,
        )
        if inserted is not None:
            try:
                telegram_events.process(spec.key)
                database.delete_state(f"telegram_event_error:{spec.key}")
            except Exception as notify_exc:
                _state(
                    f"telegram_event_error:{spec.key}",
                    {"message": str(notify_exc)[:500], "at": int(time.time() * 1000)},
                )
        final_status = "completed" if inserted is not None else "duplicate"
        final_message = "AI 前向结果已冻结" if inserted is not None else "该目标期已有更早冻结的 AI 结果"
        database.finish_forecast_job(
            lottery=spec.key,
            target_period=target_period,
            source="ai",
            status="completed",
            message=final_message,
            model=result.model,
        )
        database.delete_state(f"ai_error:{spec.key}")
        _ai_job_state(
            spec,
            status=final_status,
            target_period=target_period,
            model=result.model,
            message=final_message,
            started_at_epoch_ms=started,
            latency_ms=result.latency_ms,
        )
    except Exception as exc:
        message = str(exc)[:500]
        error = {
            "status": "error",
            "message": message,
            "target_period": target_period,
            "model": ai_config.model,
            "started_at_epoch_ms": started,
            "completed_at_epoch_ms": int(time.time() * 1000),
        }
        database.finish_forecast_job(
            lottery=spec.key,
            target_period=target_period,
            source="ai",
            status="error",
            message=message,
            model=ai_config.model,
        )
        _state(f"ai_error:{spec.key}", error)
        _ai_job_state(
            spec,
            status="error",
            target_period=target_period,
            model=ai_config.model,
            message=message,
            started_at_epoch_ms=started,
        )


def _schedule_ai_prediction(
    spec: LotterySpec,
    history: list,
    target_period: str,
    trained_through_period: str,
    ai_config: RuntimeAiConfig,
) -> bool:
    lease_ms = max(180_000, ai_config.timeout_seconds * 1000 + 60_000)
    claimed = database.claim_forecast_job(
        lottery=spec.key,
        target_period=target_period,
        source="ai",
        model=ai_config.model,
        lease_ms=lease_ms,
        retry_after_ms=AI_RETRY_AFTER_MS,
    )
    if not claimed:
        return False

    _ai_job_state(
        spec,
        status="queued",
        target_period=target_period,
        model=ai_config.model,
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


def _minimum_ai_lead_ms(ai_config: RuntimeAiConfig) -> int:
    # 不能在临近开奖时才发起长请求。120 秒超时配置至少预留 150 秒，
    # 同时上限控制在 4 分钟，避免五分钟彩种永远没有可用窗口。
    return min(240_000, max(90_000, ai_config.timeout_seconds * 1000 + 30_000))


def run_lottery_cycle(lottery_key: str, allow_ai: bool = True) -> dict[str, Any]:
    spec = LOTTERIES.get(lottery_key)
    if spec is None:
        raise KeyError(f"未知彩种：{lottery_key}")

    stages: list[dict[str, Any]] = []
    telegram_events.initialize()
    existing_count = len(database.list_draws(lottery_key, 180))
    sync_days = settings.history_days if existing_count < 180 else 2

    with _record_stage(stages, "sync_draws"):
        draws, next_period, server_time, next_draw_at = lottery_client.fetch_recent(spec, sync_days)
        database.save_draws(draws)

    with _record_stage(stages, "settle_forecasts"):
        settled = database.settle_forecasts(lottery_key)
        learning_summary = {
            "native": database.strategy_learning_summary(lottery_key, "native"),
            "ai": database.strategy_learning_summary(lottery_key, "ai"),
        }
        _state(f"learning:{lottery_key}", learning_summary)

    # Warning delivery is latency-sensitive: settle -> alert first -> routine Telegram queue.
    # This keeps two/three-miss alerts from waiting behind ordinary prediction messages.
    try:
        with _record_stage(stages, "deliver_push"):
            push_result = push_alerts.process_prediction_alerts(lottery_key)
            database.delete_state(f"push_error:{lottery_key}")
    except Exception as exc:
        push_result = {
            "created_alert_ids": [],
            "delivery": {"sent": 0, "failed": 0, "skipped": 0},
            "error": str(exc)[:500],
        }
        _state(
            f"push_error:{lottery_key}",
            {"message": str(exc)[:500], "at": int(time.time() * 1000)},
        )

    try:
        with _record_stage(stages, "deliver_telegram"):
            telegram_result = telegram_events.process(lottery_key)
            database.delete_state(f"telegram_event_error:{lottery_key}")
    except Exception as exc:
        telegram_result = {
            "created": 0,
            "delivery": {"sent": 0, "failed": 0, "skipped": 0},
            "error": str(exc)[:500],
        }
        _state(
            f"telegram_event_error:{lottery_key}",
            {"message": str(exc)[:500], "at": int(time.time() * 1000)},
        )

    with _record_stage(stages, "load_history"):
        history = database.list_draws(lottery_key, spec.history_target)
        latest = history[-1]

    generated: list[str] = []
    scheduled: list[str] = []
    errors: dict[str, str] = {}
    now_ms = int(time.time() * 1000)
    remaining_ms = None if next_draw_at is None else next_draw_at - now_ms
    before_safety_window = remaining_ms is None or remaining_ms > SAFETY_WINDOW_MS
    target_candidate = bool(
        next_period
        and next_period != "待同步"
        and before_safety_window
        and database.get_draw(lottery_key, next_period) is None
    )

    ai_config = load_ai_config()
    base_result: dict[str, Any] = {
        "lottery": lottery_key,
        "latest_period": latest.period,
        "next_period": next_period,
        "draws": len(history),
        "sync_days": sync_days,
        "settled": settled,
        "learning": learning_summary,
        "push": push_result,
        "telegram": telegram_result,
        "generated": generated,
        "scheduled": scheduled,
        "errors": errors,
        "stages": stages,
        "ai_model": ai_config.model,
        "ai_allowed": allow_ai,
        "server_time_epoch_ms": server_time,
        "next_draw_at_epoch_ms": next_draw_at,
        "remaining_to_draw_ms": remaining_ms,
        "completed_at_epoch_ms": int(time.time() * 1000),
    }
    _state(f"cycle:{lottery_key}", base_result)

    if target_candidate:
        native_model = "tianji-native-cloud-v4"
        if not database.has_forecast(lottery_key, next_period, "native", native_model):
            try:
                with _record_stage(stages, "generate_native"):
                    native_weights = database.get_strategy_weights(lottery_key, "native")
                    native = predict(history, strategy_weights=native_weights)
                    selected = native.selected
                    inserted = database.save_forecast_with_strategies(
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
                        probabilities_by_strategy=selected.strategy_probabilities,
                        weights=selected.strategy_weights,
                    )
                    if inserted is not None:
                        generated.append("native")
                if inserted is not None:
                    try:
                        with _record_stage(stages, "notify_native_result"):
                            telegram_result = telegram_events.process(lottery_key)
                            database.delete_state(f"telegram_event_error:{lottery_key}")
                    except Exception as notify_exc:
                        errors["telegram"] = str(notify_exc)[:500]
                        _state(
                            f"telegram_event_error:{lottery_key}",
                            {
                                "message": errors["telegram"],
                                "at": int(time.time() * 1000),
                            },
                        )
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

        ai_has_time = remaining_ms is None or remaining_ms > _minimum_ai_lead_ms(ai_config)
        try:
            with _record_stage(stages, "schedule_ai"):
                if (
                    allow_ai
                    and ai_config.complete
                    and ai_has_time
                    and not database.has_forecast(lottery_key, next_period, "ai", ai_config.model)
                ):
                    if _schedule_ai_prediction(spec, history, next_period, latest.period, ai_config):
                        scheduled.append("ai")
                elif allow_ai and ai_config.complete and not ai_has_time:
                    errors["ai"] = "距离开奖时间不足，本期不再启动新的 AI 请求"
                    _ai_job_state(
                        spec,
                        status="skipped",
                        target_period=next_period,
                        model=ai_config.model,
                        message=errors["ai"],
                    )
        except Exception as exc:
            errors["ai"] = str(exc)[:500]

    with _record_stage(stages, "publish_metrics"):
        base_result.update(
            {
                "telegram": telegram_result,
                "generated": generated,
                "scheduled": scheduled,
                "errors": errors,
                "stages": stages,
                "completed_at_epoch_ms": int(time.time() * 1000),
            }
        )
        _state(f"cycle:{lottery_key}", base_result)
    return base_result


def run_all_cycles(allow_ai: bool = True) -> dict[str, Any]:
    started = int(time.time() * 1000)
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}

    keys = list(LOTTERIES)
    with ThreadPoolExecutor(
        max_workers=max(1, len(keys)),
        thread_name_prefix="tianji-cycle",
    ) as pool:
        futures = {
            pool.submit(run_lottery_cycle, lottery_key, allow_ai): lottery_key
            for lottery_key in keys
        }
        for future in as_completed(futures):
            lottery_key = futures[future]
            try:
                results[lottery_key] = future.result()
            except Exception as exc:
                errors[lottery_key] = str(exc)[:500]

    completed = int(time.time() * 1000)
    heartbeat = {
        "service_version": SERVICE_VERSION,
        "started_at_epoch_ms": started,
        "completed_at_epoch_ms": completed,
        "duration_ms": max(0, completed - started),
        "ai_allowed": allow_ai,
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
