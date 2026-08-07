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
    # Imported lazily to avoid changing the main application construction path.
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
        for key, spec in LOTTERIES.items():
            realtime = _decode_state(f"realtime:{key}")
            cycle = _decode_state(f"cycle:{key}")
            lotteries.append(
                {
                    "key": key,
                    "name": spec.name,
                    "latest_period": realtime.get("latest_period") or cycle.get("latest_period"),
                    "next_period": cycle.get("next_period"),
                    "period_changed": bool(realtime.get("period_changed")),
                    "probe_latency_ms": realtime.get("probe_latency_ms"),
                    "settlement_latency_ms": realtime.get("settlement_latency_ms"),
                    "detection_delay_ms": realtime.get("detection_delay_ms"),
                    "detection_delay_ema_ms": realtime.get("detection_delay_ema_ms"),
                    "max_detection_delay_ms": realtime.get("max_detection_delay_ms"),
                    "draw_detection_samples": realtime.get("draw_detection_samples", 0),
                    "detected_at_epoch_ms": realtime.get("detected_at_epoch_ms"),
                    "updated_at_epoch_ms": realtime.get("updated_at_epoch_ms"),
                    "next_draw_at_epoch_ms": realtime.get("next_draw_at_epoch_ms")
                    or cycle.get("next_draw_at_epoch_ms"),
                }
            )
        return {
            "service_version": SERVICE_VERSION,
            "runtime_revision": os.getenv("TIANJI_RUNTIME_REVISION", "").strip(),
            "worker": _decode_state("realtime_worker_heartbeat") or _decode_state("worker_heartbeat"),
            "lotteries": lotteries,
        }
