from __future__ import annotations

import json
import time
from typing import Any

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
    # Lazy import follows realtime_admin's installation pattern and avoids changing app creation.
    from .main import app
    from .service import SERVICE_VERSION

    if any(getattr(route, "path", None) == "/v1/public/realtime" for route in app.routes):
        return

    @app.get("/v1/public/realtime", include_in_schema=False)
    def public_realtime() -> dict[str, Any]:
        lotteries: list[dict[str, Any]] = []
        for key, spec in LOTTERIES.items():
            latest = database.latest_draw(key)
            cycle = _decode_state(f"cycle:{key}")
            lotteries.append(
                {
                    "key": key,
                    "name": spec.name,
                    "latest_period": latest.period if latest else None,
                    "numbers": latest.numbers if latest else [],
                    "next_period": cycle.get("next_period", "待同步"),
                    "next_draw_at_epoch_ms": cycle.get("next_draw_at_epoch_ms"),
                    "synced_at_epoch_ms": cycle.get("completed_at_epoch_ms"),
                }
            )
        return {
            "service_version": SERVICE_VERSION,
            "generated_at_epoch_ms": int(time.time() * 1000),
            "lotteries": lotteries,
        }
