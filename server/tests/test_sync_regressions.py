from __future__ import annotations

from dataclasses import dataclass
import json
import os
from types import SimpleNamespace
import tempfile
import unittest

from app.db import Database
from app.lottery import normalize_next_period
from app.models import DrawModel
from app.runtime_config import RuntimeAiConfig
from app import service


class NextPeriodTests(unittest.TestCase):
    def test_stale_reported_issue_is_replaced(self) -> None:
        self.assertEqual(normalize_next_period("21347571", "21347570"), "21347572")
        self.assertEqual(normalize_next_period("21347571", "21347572"), "21347572")


class FakeLotteryClient:
    def __init__(self, draws: list[DrawModel], next_period: str) -> None:
        self.draws = draws
        self.next_period = next_period

    def fetch_recent(self, _spec: object, _days: int):
        return self.draws, self.next_period, 1_785_000_000_000, 1_885_000_000_000

    def fetch_latest(self, _spec: object):
        return self.draws[-1], self.next_period, 1_785_000_000_000, 1_885_000_000_000


class SyncRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(os.path.join(self.temp_dir.name, "test.db"))
        self.original_database = service.database
        self.original_client = service.lottery_client
        self.original_predict = service.predict
        self.original_load_ai = service.load_ai_config
        service.database = self.database
        service.load_ai_config = lambda: RuntimeAiConfig(
            enabled=False,
            endpoint="",
            model="",
            api_key="",
            timeout_seconds=120,
        )

    def tearDown(self) -> None:
        service.database = self.original_database
        service.lottery_client = self.original_client
        service.predict = self.original_predict
        service.load_ai_config = self.original_load_ai
        self.temp_dir.cleanup()

    @staticmethod
    def draw(period: str) -> DrawModel:
        return DrawModel(
            lottery="azxy10",
            period=period,
            numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            draw_time="2026-08-04 08:30:00",
        )

    def test_opened_forecast_settles_before_prediction_failure(self) -> None:
        self.database.save_draws([self.draw("21347571")])
        self.database.save_forecast(
            lottery="azxy10",
            target_period="21347572",
            trained_through_period="21347571",
            position=0,
            top6=[1, 2, 3, 4, 5, 6],
            top7=[1, 2, 3, 4, 5, 6, 7],
            probabilities=[0.1] * 10,
            source="native",
            model="tianji-native-cloud-v1",
            analysis="test",
            risk_note="test",
        )
        service.lottery_client = FakeLotteryClient(
            [self.draw("21347571"), self.draw("21347572"), self.draw("21347573")],
            "21347574",
        )
        service.predict = lambda _history: (_ for _ in ()).throw(RuntimeError("predict failed"))

        result = service.run_lottery_cycle("azxy10")

        self.assertEqual(result["latest_period"], "21347573")
        self.assertEqual(result["next_period"], "21347574")
        self.assertEqual(result["settled"], 1)
        settled = self.database.list_forecasts("azxy10", 10)[0]
        self.assertIsNotNone(settled.top6_hit)
        cycle_raw = self.database.get_state("cycle:azxy10")
        self.assertIsNotNone(cycle_raw)
        cycle = json.loads(cycle_raw[0])
        self.assertEqual(cycle["next_period"], "21347574")
        self.assertIn("native", cycle["errors"])


if __name__ == "__main__":
    unittest.main()
