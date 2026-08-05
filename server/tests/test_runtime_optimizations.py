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


if __name__ == "__main__":
    unittest.main()
