from __future__ import annotations

import json
import time
import unittest

from app import fixed_target_runtime_guard, telegram_events
from app.db import database
from app.models import DrawModel


class RetiredFixedTargetRuntimeGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        telegram_events.initialize()
        now = int(time.time() * 1000)
        with database.connection() as db:
            db.execute("DELETE FROM telegram_event_deliveries")
            db.execute("DELETE FROM telegram_events")
            db.execute("DELETE FROM telegram_event_state")
            db.execute("DELETE FROM forecast_strategy_predictions")
            db.execute("DELETE FROM forecasts")
            db.execute("DELETE FROM draws")
            db.executemany(
                "INSERT INTO telegram_event_state(state_key,state_value,updated_at) VALUES(?,?,?)",
                [
                    ("telegram_events_baseline_ms", "0", now),
                    ("telegram_prediction_always_from_ms_v1", "0", now),
                    ("telegram_prediction_policy_always_v3", "always_push_cloud_ai", now),
                    ("telegram_win_policy_tracking_only_v1", "recovery_after_three_misses_only", now),
                ],
            )

    def save_dynamic(self, target: str) -> int:
        forecast_id = database.save_forecast(
            lottery="xyft",
            target_period=target,
            trained_through_period=str(int(target) - 1),
            position=7,
            top6=[2, 5, 4, 10, 1, 8],
            top7=[2, 5, 4, 10, 1, 8, 3],
            probabilities=[0.05, 0.12, 0.09, 0.11, 0.14, 0.04, 0.06, 0.13, 0.08, 0.18],
            source="ai",
            model="deepseek-v4-pro",
            analysis="dynamic AI v2 row",
            risk_note="dynamic AI v2 row",
        )
        self.assertIsNotNone(forecast_id)
        return int(forecast_id)

    def settle(self, target: str, actual: int) -> None:
        numbers = [number for number in range(1, 11) if number != actual]
        numbers.insert(7, actual)
        database.save_draws([DrawModel(lottery="xyft", period=target, numbers=numbers)])
        database.settle_forecasts("xyft")

    def test_legacy_fixed_runtime_guard_is_not_installed(self) -> None:
        self.assertFalse(fixed_target_runtime_guard._INSTALLED)
        self.assertIsNone(fixed_target_runtime_guard._ORIGINAL_SETTLE)
        self.assertIsNone(fixed_target_runtime_guard._ORIGINAL_MATERIALIZE)

    def test_dynamic_row_is_settled_against_its_original_top6(self) -> None:
        forecast_id = self.save_dynamic("21349990")
        self.settle("21349990", 4)
        with database.connection() as db:
            row = db.execute(
                "SELECT top6_json,top6_hit FROM forecasts WHERE id=?",
                (forecast_id,),
            ).fetchone()
        self.assertEqual([2, 5, 4, 10, 1, 8], json.loads(str(row["top6_json"])))
        self.assertEqual(1, int(row["top6_hit"]))

    def test_number_outside_original_dynamic_top6_is_a_miss(self) -> None:
        forecast_id = self.save_dynamic("21349991")
        self.settle("21349991", 7)
        with database.connection() as db:
            row = db.execute(
                "SELECT top6_json,top6_hit FROM forecasts WHERE id=?",
                (forecast_id,),
            ).fetchone()
        self.assertEqual([2, 5, 4, 10, 1, 8], json.loads(str(row["top6_json"])))
        self.assertEqual(0, int(row["top6_hit"]))

    def test_telegram_event_uses_the_frozen_dynamic_prediction(self) -> None:
        self.save_dynamic("21349992")
        telegram_events.materialize_events("xyft")
        with database.connection() as db:
            row = db.execute(
                "SELECT message_html FROM telegram_events WHERE event_type='prediction' LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(row)
        message = str(row["message_html"])
        self.assertIn("02、05、04、10、01、08", message)
        self.assertNotIn("02、03、05、07、08、10", message)


if __name__ == "__main__":
    unittest.main()
