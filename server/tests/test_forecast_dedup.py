from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from app.db import Database


class ForecastDedupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp_dir.name, "test.db")
        self.database = Database(self.path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def save_ai(self, *, model: str, position: int) -> int | None:
        return self.database.save_forecast(
            lottery="xyft",
            target_period="20260804001",
            trained_through_period="20260803180",
            position=position,
            top6=[1, 2, 3, 4, 5, 6],
            top7=[1, 2, 3, 4, 5, 6, 7],
            probabilities=[0.1] * 10,
            source="ai",
            model=model,
            analysis="test",
            risk_note="test",
        )

    def test_model_switch_does_not_create_second_formal_prediction(self) -> None:
        first = self.save_ai(model="deepseek-v4-pro", position=2)
        second = self.save_ai(model="deepseek-v4-flash", position=9)

        self.assertIsNotNone(first)
        self.assertIsNone(second)
        records = self.database.list_forecasts("xyft", 10)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].model, "deepseek-v4-pro")
        self.assertEqual(records[0].position, 2)

    def test_job_claim_is_atomic_for_same_lottery_target_and_source(self) -> None:
        first = self.database.claim_forecast_job(
            lottery="azxy10",
            target_period="21347580",
            source="ai",
            model="deepseek-v4-flash",
            lease_ms=180_000,
        )
        second = self.database.claim_forecast_job(
            lottery="azxy10",
            target_period="21347580",
            source="ai",
            model="deepseek-v4-flash",
            lease_ms=180_000,
        )

        self.assertTrue(first)
        self.assertFalse(second)

    def test_different_lotteries_can_claim_in_parallel(self) -> None:
        xyft = self.database.claim_forecast_job(
            lottery="xyft",
            target_period="20260804001",
            source="ai",
            model="deepseek-v4-flash",
            lease_ms=180_000,
        )
        azxy10 = self.database.claim_forecast_job(
            lottery="azxy10",
            target_period="21347580",
            source="ai",
            model="deepseek-v4-flash",
            lease_ms=180_000,
        )
        self.assertTrue(xyft)
        self.assertTrue(azxy10)


class LegacyMigrationTests(unittest.TestCase):
    def test_legacy_duplicate_ai_rows_keep_earliest_frozen_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "legacy.db")
            connection = sqlite3.connect(path)
            connection.executescript(
                """
                CREATE TABLE forecasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lottery TEXT NOT NULL,
                    target_period TEXT NOT NULL,
                    trained_through_period TEXT NOT NULL,
                    position_index INTEGER NOT NULL,
                    top6_json TEXT NOT NULL,
                    top7_json TEXT NOT NULL,
                    probabilities_json TEXT NOT NULL,
                    source TEXT NOT NULL,
                    model TEXT NOT NULL,
                    analysis TEXT NOT NULL DEFAULT '',
                    risk_note TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL,
                    actual_number INTEGER,
                    top6_hit INTEGER,
                    top7_hit INTEGER,
                    settled_at INTEGER,
                    UNIQUE(lottery, target_period, source, model, position_index)
                );
                """
            )
            values = (
                "xyft",
                "20260804001",
                "20260803180",
                "[1,2,3,4,5,6]",
                "[1,2,3,4,5,6,7]",
                "[0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1]",
                "ai",
                "test",
                "test",
            )
            connection.execute(
                """
                INSERT INTO forecasts(
                    lottery,target_period,trained_through_period,position_index,
                    top6_json,top7_json,probabilities_json,source,model,
                    analysis,risk_note,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (*values[:3], 2, *values[3:7], "deepseek-v4-pro", *values[7:], 1000),
            )
            connection.execute(
                """
                INSERT INTO forecasts(
                    lottery,target_period,trained_through_period,position_index,
                    top6_json,top7_json,probabilities_json,source,model,
                    analysis,risk_note,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (*values[:3], 9, *values[3:7], "deepseek-v4-flash", *values[7:], 2000),
            )
            connection.commit()
            connection.close()

            database = Database(path)
            records = database.list_forecasts("xyft", 10)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].model, "deepseek-v4-pro")
            self.assertEqual(records[0].position, 2)


if __name__ == "__main__":
    unittest.main()
