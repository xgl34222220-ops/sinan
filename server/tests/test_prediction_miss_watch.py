from __future__ import annotations

import unittest

from app.admin_insights import _prediction_miss_watch_from_records


class PredictionMissWatchTests(unittest.TestCase):
    @staticmethod
    def record(
        lottery: str,
        source: str,
        model: str,
        period: str,
        hit: bool | None,
        created: int,
    ) -> dict:
        return {
            "lottery": lottery,
            "source": source,
            "model": model,
            "target_period": period,
            "top6_hit": hit,
            "actual_number": 8,
            "position": 0,
            "top6": [1, 2, 3, 4, 5, 6],
            "settled_at_epoch_ms": created if hit is not None else None,
            "created_at_epoch_ms": created,
        }

    def test_three_consecutive_misses_trigger_warning_with_exact_periods(self) -> None:
        records = [
            self.record("xyft", "ai", "deepseek-v4", "104", False, 104),
            self.record("xyft", "ai", "deepseek-v4", "103", False, 103),
            self.record("xyft", "ai", "deepseek-v4", "102", False, 102),
            self.record("xyft", "ai", "deepseek-v4", "101", True, 101),
        ]
        result = _prediction_miss_watch_from_records(records, threshold=3)
        xyft = next(item for item in result["lotteries"] if item["key"] == "xyft")
        prediction = xyft["predictions"][0]
        self.assertTrue(prediction["warning"])
        self.assertEqual(prediction["current_miss_streak"], 3)
        self.assertEqual(
            [item["target_period"] for item in prediction["recent_three"]],
            ["104", "103", "102"],
        )

    def test_hit_resets_streak_and_models_are_isolated(self) -> None:
        records = [
            self.record("azxy10", "native", "native-a", "204", False, 204),
            self.record("azxy10", "native", "native-a", "203", True, 203),
            self.record("azxy10", "ai", "ai-b", "204", False, 202),
            self.record("azxy10", "ai", "ai-b", "203", False, 201),
            self.record("azxy10", "ai", "ai-b", "202", False, 200),
        ]
        result = _prediction_miss_watch_from_records(records, threshold=3)
        azxy = next(item for item in result["lotteries"] if item["key"] == "azxy10")
        values = {item["model"]: item for item in azxy["predictions"]}
        self.assertFalse(values["native-a"]["warning"])
        self.assertEqual(values["native-a"]["current_miss_streak"], 1)
        self.assertTrue(values["ai-b"]["warning"])
        self.assertEqual(result["warning_count"], 1)

    def test_pending_record_does_not_count_as_miss(self) -> None:
        records = [
            self.record("xyft", "ai", "model", "304", None, 304),
            self.record("xyft", "ai", "model", "303", False, 303),
            self.record("xyft", "ai", "model", "302", False, 302),
        ]
        result = _prediction_miss_watch_from_records(records, threshold=3)
        xyft = next(item for item in result["lotteries"] if item["key"] == "xyft")
        prediction = xyft["predictions"][0]
        self.assertFalse(prediction["warning"])
        self.assertEqual(prediction["current_miss_streak"], 2)
        self.assertEqual(prediction["pending_records"], 1)


if __name__ == "__main__":
    unittest.main()
