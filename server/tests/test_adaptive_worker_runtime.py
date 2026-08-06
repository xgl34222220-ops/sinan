from __future__ import annotations

import json
import tempfile
import unittest

from app.db import Database
from app.models import DrawModel
from app.service import SERVICE_VERSION


class AdaptiveWorkerRuntimeTests(unittest.TestCase):
    def test_service_version_marks_forced_worker_runtime(self) -> None:
        self.assertEqual(SERVICE_VERSION, "1.7.2")

    def test_v4_forecast_requires_strategy_snapshot_on_settlement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(f"{directory}/missing.db")
            forecast_id = database.save_forecast(
                lottery="xyft",
                target_period="400001",
                trained_through_period="400000",
                position=0,
                top6=[1, 2, 3, 4, 5, 6],
                top7=[1, 2, 3, 4, 5, 6, 7],
                probabilities=[0.1] * 10,
                source="native",
                model="tianji-native-cloud-v4",
                analysis="missing snapshot",
                risk_note="test",
            )
            self.assertIsNotNone(forecast_id)
            database.save_draws([
                DrawModel(
                    lottery="xyft",
                    period="400001",
                    numbers=[1,2,3,4,5,6,7,8,9,10],
                )
            ])
            with self.assertRaisesRegex(RuntimeError, "缺少策略快照"):
                database.settle_forecasts("xyft")
            record = database.list_forecasts("xyft", 1)[0]
            self.assertIsNone(record.actual_number)

    def test_v4_atomic_snapshot_settles_and_updates_learning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(f"{directory}/v4.db")
            forecast_id = database.save_forecast_with_strategies(
                lottery="xyft",
                target_period="400002",
                trained_through_period="400001",
                position=0,
                top6=[1,2,3,4,5,6],
                top7=[1,2,3,4,5,6,7],
                probabilities=[0.1] * 10,
                source="native",
                model="tianji-native-cloud-v4",
                analysis="v4",
                risk_note="test",
                probabilities_by_strategy={
                    "good": [0.7] + [0.3 / 9] * 9,
                    "bad": [0.3 / 9] * 9 + [0.7],
                },
                weights={"good": 0.5, "bad": 0.5},
            )
            self.assertIsNotNone(forecast_id)
            diagnostics = database.strategy_snapshot_diagnostics("xyft")
            self.assertEqual(diagnostics[0]["snapshot_count"], 2)
            database.save_draws([
                DrawModel(
                    lottery="xyft",
                    period="400002",
                    numbers=[1,2,3,4,5,6,7,8,9,10],
                )
            ])
            self.assertEqual(database.settle_forecasts("xyft"), 1)
            learning = database.strategy_learning_summary("xyft", "native")
            self.assertEqual({row["samples"] for row in learning}, {1})
            self.assertGreater(
                next(row["weight"] for row in learning if row["strategy"] == "good"),
                next(row["weight"] for row in learning if row["strategy"] == "bad"),
            )
            diagnostics = database.strategy_snapshot_diagnostics("xyft")
            self.assertEqual(diagnostics[0]["settled_snapshot_count"], 2)


if __name__ == "__main__":
    unittest.main()
