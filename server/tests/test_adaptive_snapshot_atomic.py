from __future__ import annotations

import sqlite3
import tempfile
import unittest

from app.db import Database


class AdaptiveSnapshotAtomicTests(unittest.TestCase):
    def call(self, database: Database, *, strategies):
        return database.save_forecast_with_strategies(
            lottery="xyft",
            target_period="300001",
            trained_through_period="300000",
            position=0,
            top6=[1,2,3,4,5,6],
            top7=[1,2,3,4,5,6,7],
            probabilities=[0.1] * 10,
            source="native",
            model="atomic-v1",
            analysis="atomic",
            risk_note="test",
            probabilities_by_strategy=strategies,
            weights={name: 1 / max(1, len(strategies)) for name in strategies},
        )

    def test_forecast_and_all_strategy_snapshots_commit_together(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/atomic.db")
            forecast_id = self.call(
                db,
                strategies={"a": [0.1] * 10, "b": [0.05] * 9 + [0.55]},
            )
            self.assertIsNotNone(forecast_id)
            with db.connection() as connection:
                forecast_count = connection.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]
                snapshot_count = connection.execute(
                    "SELECT COUNT(*) FROM forecast_strategy_predictions WHERE forecast_id = ?",
                    (forecast_id,),
                ).fetchone()[0]
            self.assertEqual(forecast_count, 1)
            self.assertEqual(snapshot_count, 2)

    def test_invalid_snapshot_rolls_back_forecast(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/rollback.db")
            with self.assertRaises(ValueError):
                self.call(db, strategies={"broken": [0.1] * 9})
            with db.connection() as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0], 0)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM forecast_strategy_predictions").fetchone()[0], 0)

    def test_database_error_rolls_back_main_forecast(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/failure.db")
            with db.connection() as connection:
                connection.execute("DROP TABLE forecast_strategy_predictions")
            with self.assertRaises(sqlite3.OperationalError):
                self.call(db, strategies={"a": [0.1] * 10})
            with db.connection() as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
