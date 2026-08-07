from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.ai_position_failover_guard import (
    _apply_failover,
    _leading_same_position_misses,
)


class AiPositionFailoverGuardTest(unittest.TestCase):
    def review(self, best: int) -> SimpleNamespace:
        scores = [0.01] * 10
        scores[best] = 0.91
        return SimpleNamespace(scores=scores)

    def forecast(self, *, position: int, hit: bool, model: str = "deepseek-v4-pro") -> SimpleNamespace:
        return SimpleNamespace(
            source="ai",
            model=model,
            position=position,
            top6_hit=hit,
            actual_number=4 if not hit else 7,
        )

    def test_one_miss_does_not_force_rotation(self) -> None:
        combined = [0.20, 0.19] + [0.07625] * 8
        adjusted, selected, note = _apply_failover(
            combined,
            [self.review(1), self.review(1), self.review(1)],
            failed_position=0,
            miss_count=1,
        )
        self.assertEqual(combined, adjusted)
        self.assertEqual(0, selected)
        self.assertIn("未触发", note)

    def test_two_same_position_misses_allow_ai_to_break_close_tie(self) -> None:
        combined = [0.205, 0.195] + [0.075] * 8
        _adjusted, selected, note = _apply_failover(
            combined,
            [self.review(1), self.review(1), self.review(1)],
            failed_position=0,
            miss_count=2,
        )
        self.assertEqual(1, selected)
        self.assertIn("切换", note)

    def test_three_same_position_misses_force_one_cycle_cooldown(self) -> None:
        combined = [0.40, 0.16, 0.14, 0.10, 0.08, 0.04, 0.03, 0.02, 0.02, 0.01]
        _adjusted, selected, note = _apply_failover(
            combined,
            [self.review(0), self.review(0), self.review(0)],
            failed_position=0,
            miss_count=3,
        )
        self.assertEqual(1, selected)
        self.assertIn("硬冷却", note)

    def test_latest_hit_resets_failed_recommendation_streak(self) -> None:
        forecasts = [
            self.forecast(position=1, hit=True),
            self.forecast(position=1, hit=False),
            self.forecast(position=1, hit=False),
        ]
        position, count = _leading_same_position_misses(
            forecasts,
            model="deepseek-v4-pro",
        )
        self.assertIsNone(position)
        self.assertEqual(0, count)

    def test_consecutive_failures_are_model_and_position_specific(self) -> None:
        forecasts = [
            self.forecast(position=1, hit=False),
            self.forecast(position=1, hit=False),
            self.forecast(position=2, hit=False),
            self.forecast(position=1, hit=False),
        ]
        position, count = _leading_same_position_misses(
            forecasts,
            model="deepseek-v4-pro",
        )
        self.assertEqual(1, position)
        self.assertEqual(2, count)


if __name__ == "__main__":
    unittest.main()
