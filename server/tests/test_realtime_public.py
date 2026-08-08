from __future__ import annotations

import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import realtime_public


class RealtimePublicTests(unittest.TestCase):
    def test_public_realtime_payload_contains_both_lotteries(self) -> None:
        periods = {
            "xyft": ("101", list(range(1, 11))),
            "azxy10": ("201", list(range(10, 0, -1))),
        }

        def latest_draw(key: str):
            period, numbers = periods[key]
            return SimpleNamespace(period=period, numbers=numbers)

        def get_state(key: str):
            lottery = key.split(":", 1)[1]
            next_period = "102" if lottery == "xyft" else "202"
            payload = {
                "next_period": next_period,
                "next_draw_at_epoch_ms": 20_000 if lottery == "xyft" else 30_000,
                "completed_at_epoch_ms": 15_000 if lottery == "xyft" else 16_000,
            }
            return json.dumps(payload), 17_000

        with (
            patch.object(realtime_public.database, "latest_draw", side_effect=latest_draw),
            patch.object(realtime_public.database, "get_state", side_effect=get_state),
        ):
            payload = realtime_public.public_realtime_payload(now_ms=18_000)

        self.assertEqual(18_000, payload["generated_at_epoch_ms"])
        rows = {row["key"]: row for row in payload["lotteries"]}
        self.assertEqual({"xyft", "azxy10"}, set(rows))
        self.assertEqual("101", rows["xyft"]["latest_period"])
        self.assertEqual("102", rows["xyft"]["next_period"])
        self.assertEqual(list(range(10, 0, -1)), rows["azxy10"]["numbers"])
        self.assertEqual(16_000, rows["azxy10"]["synced_at_epoch_ms"])

    def test_public_realtime_route_is_installed(self) -> None:
        from app.main import app

        self.assertTrue(
            any(getattr(route, "path", None) == "/v1/public/realtime" for route in app.routes)
        )


if __name__ == "__main__":
    unittest.main()
