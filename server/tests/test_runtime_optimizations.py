from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import Database
from app.models import DrawModel
from app.runtime_optimizations import _batch_settle_forecasts


class RuntimeOptimizationsTest(unittest.TestCase):
    def test_batch_settlement_joins_draws_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(str(Path(directory) / "runtime.db"))
            database.save_draws(
                [
                    DrawModel(
                        lottery="xyft",
                        period="202608050100",
                        numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                    )
                ]
            )
            inserted = database.save_forecast(
                lottery="xyft",
                target_period="202608050100",
                trained_through_period="202608050099",
                position=1,
                top6=[2, 3, 4, 5, 6, 7],
                top7=[2, 3, 4, 5, 6, 7, 8],
                probabilities=[0.1] * 10,
                source="native",
                model="test-model",
                analysis="测试",
                risk_note="测试",
            )
            self.assertIsNotNone(inserted)

            settled = _batch_settle_forecasts(database, "xyft")

            self.assertEqual(settled, 1)
            record = database.list_forecasts("xyft", 1)[0]
            self.assertEqual(record.actual_number, 2)
            self.assertTrue(record.top6_hit)
            self.assertTrue(record.top7_hit)


    def test_runtime_hook_reconciles_learning_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(str(Path(directory) / "learning.db"))
            forecast_id = database.save_forecast_with_strategies(
                lottery="xyft",
                target_period="202608050101",
                trained_through_period="202608050100",
                position=0,
                top6=[1, 2, 3, 4, 5, 6],
                top7=[1, 2, 3, 4, 5, 6, 7],
                probabilities=[0.1] * 10,
                source="native",
                model="tianji-native-cloud-v4",
                analysis="学习补偿测试",
                risk_note="测试",
                probabilities_by_strategy={
                    "good": [0.7] + [0.3 / 9] * 9,
                    "bad": [0.3 / 9] * 9 + [0.7],
                },
                weights={"good": 0.5, "bad": 0.5},
            )
            self.assertIsNotNone(forecast_id)
            with database.connection() as db:
                db.execute(
                    """
                    UPDATE forecasts SET
                        actual_number = 1, top6_hit = 1, top7_hit = 1, settled_at = 123456789
                    WHERE id = ?
                    """,
                    (forecast_id,),
                )

            self.assertEqual(_batch_settle_forecasts(database, "xyft"), 1)
            learning = database.strategy_learning_summary("xyft", "native")
            self.assertEqual({row["samples"] for row in learning}, {1})
            diagnostics = database.strategy_snapshot_diagnostics("xyft")
            self.assertEqual(diagnostics[0]["settled_snapshot_count"], 2)
            self.assertEqual(_batch_settle_forecasts(database, "xyft"), 0)


if __name__ == "__main__":
    unittest.main()
