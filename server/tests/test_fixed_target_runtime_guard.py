from __future__ import annotations

import json
import time
import unittest

from app import fixed_target_runtime_guard, telegram_events
from app.db import database
from app.models import DrawModel


class FixedTargetRuntimeGuardTest(unittest.TestCase):
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

    def save_legacy_dynamic(self, target: str) -> int:
        forecast_id = database.save_forecast(
            lottery="xyft",
            target_period=target,
            trained_through_period=str(int(target) - 1),
            position=7,
            top6=[2, 5, 4, 10, 1, 8],
            top7=[2, 5, 4, 10, 1, 8, 3],
            probabilities=[0.1] * 10,
            source="ai",
            model="deepseek-v4-pro",
            analysis="legacy dynamic row",
            risk_note="legacy dynamic row",
        )
        self.assertIsNotNone(forecast_id)
        return int(forecast_id)

    def settle(self, target: str, actual: int) -> None:
        # The forecast selects position index 7 (第8名), so place the simulated
        # actual number at that exact position instead of position 1.
        numbers = [number for number in range(1, 11) if number != actual]
        numbers.insert(7, actual)
        database.save_draws([DrawModel(lottery="xyft", period=target, numbers=numbers)])
        database.settle_forecasts("xyft")

    def test_legacy_dynamic_row_is_settled_against_fixed_pool(self) -> None:
        forecast_id = self.save_legacy_dynamic("21349990")
        self.settle("21349990", 4)
        with database.connection() as db:
            row = db.execute(
                "SELECT top6_json,top6_hit FROM forecasts WHERE id=?",
                (forecast_id,),
            ).fetchone()
        self.assertEqual([2, 3, 5, 7, 8, 10], json.loads(str(row["top6_json"])))
        self.assertEqual(0, int(row["top6_hit"]))

    def test_fixed_pool_number_is_a_hit(self) -> None:
        forecast_id = self.save_legacy_dynamic("21349991")
        self.settle("21349991", 7)
        with database.connection() as db:
            row = db.execute(
                "SELECT top6_json,top6_hit FROM forecasts WHERE id=?",
                (forecast_id,),
            ).fetchone()
        self.assertEqual([2, 3, 5, 7, 8, 10], json.loads(str(row["top6_json"])))
        self.assertEqual(1, int(row["top6_hit"]))

    def test_telegram_event_is_materialized_from_fixed_pool(self) -> None:
        self.save_legacy_dynamic("21349992")
        telegram_events.materialize_events("xyft")
        with database.connection() as db:
            row = db.execute(
                "SELECT message_html FROM telegram_events WHERE event_type='prediction' LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(row)
        message = str(row["message_html"])
        self.assertIn("02、03、05、07、08、10", message)
        self.assertNotIn("02、05、04、10、01、08", message)

    def test_stable_estimator_does_not_use_miss_streak_as_rebound_bonus(self) -> None:
        target = {2, 3, 5, 7, 8, 10}
        mostly_hit = [2 if index % 5 else 4 for index in range(240)]
        same_history_with_recent_misses = [*mostly_hit[:-4], 4, 6, 9, 1]
        base = fixed_target_runtime_guard._stable_probability(mostly_hit)
        recent_misses = fixed_target_runtime_guard._stable_probability(same_history_with_recent_misses)
        self.assertGreater(base, 0.60)
        self.assertLess(recent_misses, base)
        self.assertTrue(all((number in target) == fixed_target_runtime_guard._is_target(number) for number in range(1, 11)))


if __name__ == "__main__":
    unittest.main()
