from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
import json
import logging
import random
import signal
import threading
import time
from typing import Any

from .config import settings
from .runtime_optimizations import cleanup_runtime_state, install as install_runtime_optimizations

install_runtime_optimizations()

from .runtime_config import load_ai_config  # noqa: E402
from .service import run_all_cycles  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("tianji.worker")
stop_event = threading.Event()


def _log(level: int, event: str, **payload: Any) -> None:
    logger.log(
        level,
        json.dumps(
            {
                "event": event,
                "at_epoch_ms": int(time.time() * 1000),
                **payload,
            },
            ensure_ascii=False,
            default=str,
        ),
    )


def _stop(signum: int, _frame: object) -> None:
    _log(logging.INFO, "worker_stop_requested", signal=signum)
    stop_event.set()


def _cycle_has_errors(result: dict[str, Any]) -> bool:
    if result.get("errors"):
        return True
    for value in (result.get("results") or {}).values():
        if isinstance(value, dict) and value.get("errors"):
            return True
    return False


def _wait_with_jitter(seconds: float) -> None:
    jitter = random.uniform(0.88, 1.12)
    stop_event.wait(max(1.0, seconds * jitter))


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    active = load_ai_config()
    _log(
        logging.INFO,
        "worker_started",
        poll_seconds=settings.poll_seconds,
        cycle_timeout_seconds=settings.worker_cycle_timeout_seconds,
        ai_model=active.model if active.complete else None,
    )

    failure_streak = 0
    cycle_count = 0
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tianji-worker-cycle")
    try:
        while not stop_event.is_set():
            cycle_count += 1
            cycle_started = time.monotonic()
            future = executor.submit(run_all_cycles)
            timed_out = False
            try:
                result = future.result(timeout=settings.worker_cycle_timeout_seconds)
            except TimeoutError:
                timed_out = True
                _log(
                    logging.WARNING,
                    "worker_cycle_slow",
                    cycle=cycle_count,
                    timeout_seconds=settings.worker_cycle_timeout_seconds,
                )
                while not future.done() and not stop_event.wait(5.0):
                    _log(logging.WARNING, "worker_cycle_still_running", cycle=cycle_count)
                if stop_event.is_set() and not future.done():
                    break
                try:
                    result = future.result()
                except Exception as exc:
                    result = {"results": {}, "errors": {"worker": str(exc)[:500]}}
            except Exception as exc:
                result = {"results": {}, "errors": {"worker": str(exc)[:500]}}
                _log(
                    logging.ERROR,
                    "worker_cycle_exception",
                    cycle=cycle_count,
                    error=str(exc)[:500],
                )

            elapsed = time.monotonic() - cycle_started
            failed = timed_out or _cycle_has_errors(result)
            if failed:
                failure_streak += 1
            else:
                failure_streak = 0

            _log(
                logging.WARNING if failed else logging.INFO,
                "worker_cycle_completed",
                cycle=cycle_count,
                duration_seconds=round(elapsed, 2),
                failure_streak=failure_streak,
                errors=result.get("errors") or {},
                lotteries={
                    key: {
                        "latest_period": value.get("latest_period"),
                        "next_period": value.get("next_period"),
                        "generated": value.get("generated") or [],
                        "scheduled": value.get("scheduled") or [],
                        "errors": value.get("errors") or {},
                    }
                    for key, value in (result.get("results") or {}).items()
                    if isinstance(value, dict)
                },
            )

            if cycle_count % 20 == 0:
                try:
                    maintenance = cleanup_runtime_state()
                    _log(logging.INFO, "worker_maintenance", **maintenance)
                except Exception as exc:
                    _log(logging.WARNING, "worker_maintenance_failed", error=str(exc)[:500])

            normal_wait = max(1.0, settings.poll_seconds - elapsed)
            if failure_streak > 0:
                backoff = min(
                    settings.worker_backoff_max_seconds,
                    settings.poll_seconds * (2 ** min(failure_streak, 6)),
                )
                _wait_with_jitter(max(normal_wait, float(backoff)))
            else:
                _wait_with_jitter(normal_wait)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
        _log(logging.INFO, "worker_stopped")


if __name__ == "__main__":
    main()
