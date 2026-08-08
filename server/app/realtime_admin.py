from __future__ import annotations

import json
import os
from typing import Any

from fastapi import Depends

from .db import database
from .models import LOTTERIES


def _decode_state(key: str) -> dict[str, Any]:
    value = database.get_state(key)
    if value is None:
        return {}
    try:
        decoded = json.loads(value[0])
        return decoded if isinstance(decoded, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def install() -> None:
    from .main import app, require_admin_session
    from .service import SERVICE_VERSION

    if any(getattr(route, "path", None) == "/admin/api/realtime" for route in app.routes):
        return

    @app.get(
        "/admin/api/realtime",
        dependencies=[Depends(require_admin_session)],
        include_in_schema=False,
    )
    def admin_realtime_metrics() -> dict[str, Any]:
        lotteries: list[dict[str, Any]] = []
        full_cycle = _decode_state("full_cycle_metrics")
        for key, spec in LOTTERIES.items():
            realtime = _decode_state(f"realtime:{key}")
            cycle = _decode_state(f"cycle:{key}")
            notify = _decode_state(f"notify:{key}")
            lotteries.append(
                {
                    "key": key,
                    "name": spec.name,
                    "latest_period": realtime.get("latest_period") or cycle.get("latest_period"),
                    "next_period": cycle.get("next_period"),
                    "period_changed": bool(realtime.get("period_changed")),
                    "probe_latency_ms": realtime.get("probe_latency_ms"),
                    "probe_latency_p50_ms": realtime.get("probe_latency_p50_ms"),
                    "probe_latency_p95_ms": realtime.get("probe_latency_p95_ms"),
                    "settlement_latency_ms": realtime.get("settlement_latency_ms"),
                    "settlement_latency_p50_ms": realtime.get("settlement_latency_p50_ms"),
                    "settlement_latency_p95_ms": realtime.get("settlement_latency_p95_ms"),
                    "detection_delay_ms": realtime.get("detection_delay_ms"),
                    "detection_delay_ema_ms": realtime.get("detection_delay_ema_ms"),
                    "detection_delay_p50_ms": realtime.get("detection_delay_p50_ms"),
                    "detection_delay_p95_ms": realtime.get("detection_delay_p95_ms"),
                    "max_detection_delay_ms": realtime.get("max_detection_delay_ms"),
                    "draw_detection_samples": realtime.get("draw_detection_samples", 0),
                    "detected_at_epoch_ms": realtime.get("detected_at_epoch_ms"),
                    "updated_at_epoch_ms": realtime.get("updated_at_epoch_ms"),
                    "next_draw_at_epoch_ms": realtime.get("next_draw_at_epoch_ms") or cycle.get("next_draw_at_epoch_ms"),
                    "delivery_latency_ms": notify.get("delivery_latency_ms"),
                    "delivery_p50_ms": notify.get("delivery_p50_ms"),
                    "delivery_p95_ms": notify.get("delivery_p95_ms"),
                    "push_latency_ms": notify.get("push_latency_ms"),
                    "push_p50_ms": notify.get("push_p50_ms"),
                    "push_p95_ms": notify.get("push_p95_ms"),
                    "telegram_latency_ms": notify.get("telegram_latency_ms"),
                    "telegram_p50_ms": notify.get("telegram_p50_ms"),
                    "telegram_p95_ms": notify.get("telegram_p95_ms"),
                    "push_ok": notify.get("push_ok"),
                    "telegram_ok": notify.get("telegram_ok"),
                    "delivery_completed_at_epoch_ms": notify.get("completed_at_epoch_ms"),
                    "full_cycle_duration_ms": full_cycle.get("duration_ms"),
                    "full_cycle_p50_ms": full_cycle.get("duration_p50_ms"),
                    "full_cycle_p95_ms": full_cycle.get("duration_p95_ms"),
                    "full_cycle_completed_at_epoch_ms": full_cycle.get("completed_at_epoch_ms"),
                }
            )
        return {
            "service_version": SERVICE_VERSION,
            "runtime_revision": os.getenv("TIANJI_RUNTIME_REVISION", "").strip(),
            "worker": _decode_state("realtime_worker_heartbeat") or _decode_state("worker_heartbeat"),
            "full_cycle": full_cycle,
            "lotteries": lotteries,
        }
