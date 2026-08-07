from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
import json
import logging
import os
import random
import signal
import threading
import time
from typing import Any

from . import push_alerts, telegram_events
from .config import settings
from .db import database
from .lottery import parse_epoch_ms
from .models import LOTTERIES
from .realtime_lottery import realtime_lottery_client
from .runtime_optimizations import cleanup_runtime_state, install as install_runtime_optimizations

install_runtime_optimizations()

from .service import SERVICE_VERSION, run_all_cycles  # noqa: E402


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("tianji.realtime_worker")
stop_event = threading.Event()

_FAST_WINDOW_BEFORE_MS = 60_000
_FAST_WINDOW_AFTER_MS = 90_000
_NEAR_WINDOW_MS = 180_000
_FULL_CYCLE_INTERVAL_SECONDS = max(45.0, min(120.0, settings.poll_seconds * 2.0))
_MAINTENANCE_INTERVAL_SECONDS = 10 * 60.0
_NOTIFY_EXECUTOR = ThreadPoolExecutor(
    max_workers=max(2, len(LOTTERIES) * 2),
    thread_name_prefix="tianji-notify",
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _log(level: int, event: str, **payload: Any) -> None:
    logger.log(
        level,
        json.dumps(
            {"event": event, "at_epoch_ms": _now_ms(), **payload},
            ensure_ascii=False,
            default=str,
        ),
    )


def _stop(signum: int, _frame: object) -> None:
    _log(logging.INFO, "realtime_worker_stop_requested", signal=signum)
    stop_event.set()


def _decode_state(key: str) -> dict[str, Any]:
    value = database.get_state(key)
    if value is None:
        return {}
    try:
        parsed = json.loads(value[0])
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _set_state(key: str, payload: dict[str, Any]) -> None:
    database.set_state(key, json.dumps(payload, ensure_ascii=False, default=str))


def _patch_cycle_state(
    lottery_key: str,
    *,
    latest_period: str,
    next_period: str,
    server_time: int | None,
    next_draw_at: int | None,
    detected_at: int,
    remaining_ms: int | None,
    period_changed: bool,
    probe_latency_ms: int,
) -> None:
    cycle = _decode_state(f"cycle:{lottery_key}")
    cycle.update(
        {
            "lottery": lottery_key,
            "latest_period": latest_period,
            "next_period": next_period,
            "server_time_epoch_ms": server_time,
            "next_draw_at_epoch_ms": next_draw_at,
            "remaining_to_draw_ms": remaining_ms,
            "completed_at_epoch_ms": detected_at,
            "realtime_probe": {
                "period_changed": period_changed,
                "probe_latency_ms": probe_latency_ms,
                "detected_at_epoch_ms": detected_at,
            },
        }
    )
    _set_state(f"cycle:{lottery_key}", cycle)


def _record_realtime_metrics(
    lottery_key: str,
    *,
    previous_period: str | None,
    latest_period: str,
    period_changed: bool,
    draw_time: str,
    detected_at: int,
    probe_latency_ms: int,
    settlement_latency_ms: int,
    next_draw_at: int | None,
    remaining_ms: int | None,
) -> dict[str, Any]:
    previous = _decode_state(f"realtime:{lottery_key}")
    prior_samples = int(previous.get("draw_detection_samples") or 0)
    prior_ema = previous.get("detection_delay_ema_ms")
    draw_at = parse_epoch_ms(draw_time)
    detection_delay_ms: int | None = None
    sample_count = prior_samples
    ema: float | None = float(prior_ema) if isinstance(prior_ema, (int, float)) else None
    max_delay = int(previous.get("max_detection_delay_ms") or 0)

    if period_changed and draw_at is not None:
        detection_delay_ms = max(0, detected_at - draw_at)
        sample_count += 1
        ema = (
            float(detection_delay_ms)
            if ema is None
            else round(ema * 0.8 + detection_delay_ms * 0.2, 1)
        )
        max_delay = max(max_delay, detection_delay_ms)

    payload = {
        "lottery": lottery_key,
        "previous_period": previous_period,
        "latest_period": latest_period,
        "period_changed": period_changed,
        "draw_time": draw_time,
        "draw_time_epoch_ms": draw_at,
        "detected_at_epoch_ms": detected_at,
        "detection_delay_ms": detection_delay_ms,
        "detection_delay_ema_ms": ema,
        "max_detection_delay_ms": max_delay,
        "draw_detection_samples": sample_count,
        "probe_latency_ms": probe_latency_ms,
        "settlement_latency_ms": settlement_latency_ms,
        "next_draw_at_epoch_ms": next_draw_at,
        "remaining_to_draw_ms": remaining_ms,
        "transport": "persistent-httpx-keepalive",
        "updated_at_epoch_ms": detected_at,
    }
    _set_state(f"realtime:{lottery_key}", payload)
    return payload


def _after_draw_notifications(lottery_key: str) -> None:
    """Run network delivery outside the realtime probe loop.

    Warning creation is attempted first, then the ordinary Telegram event stream. A second push
    pass mirrors any newly-created prediction/recovery Telegram events to the App/FCM archive.
    """
    try:
        push_alerts.process_prediction_alerts(lottery_key)
        database.delete_state(f"push_error:{lottery_key}")
    except Exception as exc:  # noqa: BLE001
        _set_state(
            f"push_error:{lottery_key}",
            {"message": str(exc)[:500], "at": _now_ms(), "source": "realtime"},
        )
    try:
        telegram_events.process(lottery_key)
        database.delete_state(f"telegram_event_error:{lottery_key}")
    except Exception as exc:  # noqa: BLE001
        _set_state(
            f"telegram_event_error:{lottery_key}",
            {"message": str(exc)[:500], "at": _now_ms(), "source": "realtime"},
        )
    try:
        push_alerts.process_prediction_alerts(lottery_key)
    except Exception:
        pass


class FullCycleScheduler:
    """Coalesce slow history/prediction cycles behind the realtime probe lane."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tianji-full-cycle")
        self._lock = threading.Lock()
        self._future: Future[None] | None = None
        self._started_monotonic: float | None = None
        self._rerun_requested = False
        self._last_requested_monotonic = 0.0

    def request(self, reason: str) -> bool:
        with self._lock:
            self._last_requested_monotonic = time.monotonic()
            if self._future is not None and not self._future.done():
                self._rerun_requested = True
                return False
            self._started_monotonic = time.monotonic()
            self._future = self._executor.submit(self._run_loop, reason)
            return True

    def _run_loop(self, initial_reason: str) -> None:
        reason = initial_reason
        while not stop_event.is_set():
            started = time.monotonic()
            try:
                result = run_all_cycles()
                _log(
                    logging.INFO,
                    "full_cycle_completed",
                    reason=reason,
                    duration_seconds=round(time.monotonic() - started, 2),
                    errors=result.get("errors") or {},
                )
                database.delete_state("full_cycle_error")
            except Exception as exc:  # noqa: BLE001
                _set_state(
                    "full_cycle_error",
                    {"message": str(exc)[:500], "at": _now_ms(), "reason": reason},
                )
                _log(
                    logging.ERROR,
                    "full_cycle_failed",
                    reason=reason,
                    error=str(exc)[:500],
                )

            with self._lock:
                if self._rerun_requested and not stop_event.is_set():
                    self._rerun_requested = False
                    self._started_monotonic = time.monotonic()
                    reason = "coalesced-rerun"
                    continue
                self._future = None
                self._started_monotonic = None
                return

    def is_due(self) -> bool:
        with self._lock:
            return time.monotonic() - self._last_requested_monotonic >= _FULL_CYCLE_INTERVAL_SECONDS

    def overdue(self) -> bool:
        with self._lock:
            if self._future is None or self._future.done() or self._started_monotonic is None:
                return False
            return time.monotonic() - self._started_monotonic > settings.worker_cycle_timeout_seconds

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


def _probe_one(lottery_key: str, scheduler: FullCycleScheduler) -> dict[str, Any]:
    spec = LOTTERIES[lottery_key]
    started = time.monotonic()
    previous = database.latest_draw(lottery_key)
    previous_period = previous.period if previous is not None else None

    latest, next_period, server_time, next_draw_at = realtime_lottery_client.fetch_latest(spec)
    detected_at = _now_ms()
    probe_latency_ms = max(0, round((time.monotonic() - started) * 1000))
    period_changed = previous_period != latest.period

    # Saving the single latest draw is deliberately first. History repair happens in the slow lane.
    database.save_draws([latest])

    settlement_latency_ms = 0
    settled = 0
    notification_queued = False
    full_cycle_queued = False
    if period_changed:
        settle_started = time.monotonic()
        settled = database.settle_forecasts(lottery_key)
        settlement_latency_ms = max(0, round((time.monotonic() - settle_started) * 1000))
        learning_summary = {
            "native": database.strategy_learning_summary(lottery_key, "native"),
            "ai": database.strategy_learning_summary(lottery_key, "ai"),
        }
        _set_state(f"learning:{lottery_key}", learning_summary)
        _NOTIFY_EXECUTOR.submit(_after_draw_notifications, lottery_key)
        notification_queued = True
        full_cycle_queued = scheduler.request(f"new-draw:{lottery_key}:{latest.period}")

    now = _now_ms()
    remaining_ms = None if next_draw_at is None else next_draw_at - now
    _patch_cycle_state(
        lottery_key,
        latest_period=latest.period,
        next_period=next_period,
        server_time=server_time,
        next_draw_at=next_draw_at,
        detected_at=detected_at,
        remaining_ms=remaining_ms,
        period_changed=period_changed,
        probe_latency_ms=probe_latency_ms,
    )
    metrics = _record_realtime_metrics(
        lottery_key,
        previous_period=previous_period,
        latest_period=latest.period,
        period_changed=period_changed,
        draw_time=latest.draw_time,
        detected_at=detected_at,
        probe_latency_ms=probe_latency_ms,
        settlement_latency_ms=settlement_latency_ms,
        next_draw_at=next_draw_at,
        remaining_ms=remaining_ms,
    )
    return {
        "lottery": lottery_key,
        "latest_period": latest.period,
        "next_period": next_period,
        "period_changed": period_changed,
        "settled": settled,
        "notification_queued": notification_queued,
        "full_cycle_queued": full_cycle_queued,
        "server_time_epoch_ms": server_time,
        "next_draw_at_epoch_ms": next_draw_at,
        "remaining_to_draw_ms": remaining_ms,
        "probe_latency_ms": probe_latency_ms,
        "detection_delay_ms": metrics.get("detection_delay_ms"),
        "generated": [],
        "scheduled": [],
        "errors": {},
    }


def _probe_all(scheduler: FullCycleScheduler) -> tuple[dict[str, Any], dict[str, str]]:
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(
        max_workers=max(1, len(LOTTERIES)),
        thread_name_prefix="tianji-realtime-probe",
    ) as pool:
        futures = {
            pool.submit(_probe_one, lottery_key, scheduler): lottery_key
            for lottery_key in LOTTERIES
        }
        for future in as_completed(futures):
            lottery_key = futures[future]
            try:
                results[lottery_key] = future.result()
            except Exception as exc:  # noqa: BLE001
                errors[lottery_key] = str(exc)[:500]
                _set_state(
                    f"realtime_error:{lottery_key}",
                    {"message": errors[lottery_key], "at": _now_ms()},
                )
    return results, errors


def _recommended_wait_seconds(results: dict[str, Any], errors: dict[str, str]) -> float:
    base = float(max(10, min(60, settings.poll_seconds)))
    wait = base
    for value in results.values():
        remaining = value.get("remaining_to_draw_ms")
        if not isinstance(remaining, (int, float)):
            continue
        if -_FAST_WINDOW_AFTER_MS <= remaining <= _FAST_WINDOW_BEFORE_MS:
            wait = min(wait, 2.0)
        elif 0 < remaining <= _NEAR_WINDOW_MS:
            wait = min(wait, 6.0)
    if errors:
        wait = min(wait, 5.0)
    return wait


def _write_heartbeat(
    *,
    started_at: int,
    results: dict[str, Any],
    errors: dict[str, str],
    wait_seconds: float,
) -> None:
    completed = _now_ms()
    heartbeat = {
        "service_version": f"{SERVICE_VERSION}+realtime1",
        "worker_mode": "realtime-split-lane",
        "started_at_epoch_ms": started_at,
        "completed_at_epoch_ms": completed,
        "duration_ms": max(0, completed - started_at),
        "next_probe_seconds": wait_seconds,
        "ai_allowed": True,
        "results": results,
        "errors": errors,
    }
    _set_state("realtime_worker_heartbeat", heartbeat)
    # Existing health/admin code reads worker_heartbeat, so keep it fresh without changing the API.
    _set_state("worker_heartbeat", heartbeat)


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    push_alerts.initialize()
    telegram_events.initialize()
    scheduler = FullCycleScheduler()
    scheduler.request("startup")
    next_maintenance = time.monotonic() + _MAINTENANCE_INTERVAL_SECONDS

    _log(
        logging.INFO,
        "realtime_worker_started",
        service_version=SERVICE_VERSION,
        base_poll_seconds=settings.poll_seconds,
        full_cycle_interval_seconds=_FULL_CYCLE_INTERVAL_SECONDS,
        fast_probe_seconds=2,
    )

    try:
        while not stop_event.is_set():
            cycle_started_ms = _now_ms()
            results, errors = _probe_all(scheduler)

            if scheduler.is_due():
                scheduler.request("periodic-maintenance-cycle")
            if scheduler.overdue():
                payload = {
                    "timeout_seconds": settings.worker_cycle_timeout_seconds,
                    "at_epoch_ms": _now_ms(),
                    "action": "process_restart",
                }
                _set_state("worker_hard_timeout", payload)
                _log(logging.CRITICAL, "full_cycle_hard_timeout", **payload)
                os._exit(70)

            if time.monotonic() >= next_maintenance:
                try:
                    _log(logging.INFO, "worker_maintenance", **cleanup_runtime_state())
                except Exception as exc:  # noqa: BLE001
                    _log(logging.WARNING, "worker_maintenance_failed", error=str(exc)[:500])
                next_maintenance = time.monotonic() + _MAINTENANCE_INTERVAL_SECONDS

            wait_seconds = _recommended_wait_seconds(results, errors)
            _write_heartbeat(
                started_at=cycle_started_ms,
                results=results,
                errors=errors,
                wait_seconds=wait_seconds,
            )
            _log(
                logging.WARNING if errors else logging.INFO,
                "realtime_probe_completed",
                duration_ms=max(0, _now_ms() - cycle_started_ms),
                next_probe_seconds=wait_seconds,
                lotteries={
                    key: {
                        "latest_period": value.get("latest_period"),
                        "next_period": value.get("next_period"),
                        "period_changed": value.get("period_changed"),
                        "probe_latency_ms": value.get("probe_latency_ms"),
                        "detection_delay_ms": value.get("detection_delay_ms"),
                    }
                    for key, value in results.items()
                },
                errors=errors,
            )

            actual_wait = wait_seconds
            if wait_seconds >= 10:
                actual_wait *= random.uniform(0.94, 1.06)
            stop_event.wait(max(0.5, actual_wait))
    finally:
        scheduler.shutdown()
        _NOTIFY_EXECUTOR.shutdown(wait=False, cancel_futures=True)
        realtime_lottery_client.close()
        _log(logging.INFO, "realtime_worker_stopped")


if __name__ == "__main__":
    main()
