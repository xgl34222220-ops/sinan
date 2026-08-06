from __future__ import annotations

import unittest

from app.continual_learning import (
    STRUCTURAL_STRATEGIES,
    build_position_profile,
    continual_strategy_components,
    learn_position_weights,
)
from app.models import DrawModel
from app.predictor import predict


class ContinualLearningTest(unittest.TestCase):
    def history(self, count: int = 180) -> list[DrawModel]:
        draws: list[DrawModel] = []
        for index in range(count):
            first = (index % 3) * 3 + 1
            first = min(first, 10)
            second = 8 if index % 5 else 2
            ordered: list[int] = []
            for value in (first, second, *range(1, 11)):
                if value not in ordered:
                    ordered.append(value)
            draws.append(
                DrawModel(
                    lottery="azxy10",
                    period=str(index + 1).zfill(6),
                    numbers=ordered[:10],
                    draw_time="2026-08-01 00:00:00",
                )
            )
        return draws

    def test_structural_strategies_are_real_probability_vectors(self) -> None:
        components = continual_strategy_components(self.history(), 0)
        for strategy in STRUCTURAL_STRATEGIES:
            self.assertIn(strategy, components)
            self.assertEqual(10, len(components[strategy]))
            self.assertAlmostEqual(1.0, sum(components[strategy]), places=9)
            self.assertTrue(all(value > 0 for value in components[strategy]))

    def test_each_position_learns_its_own_normalized_weights(self) -> None:
        history = self.history()
        first = learn_position_weights(history, 0)
        second = learn_position_weights(history, 1)
        self.assertAlmostEqual(1.0, sum(first.values()), places=9)
        self.assertAlmostEqual(1.0, sum(second.values()), places=9)
        self.assertEqual(set(first), set(second))
        self.assertNotEqual(first, second)

    def test_profile_uses_forward_holdout_and_reports_miss_streak(self) -> None:
        profile = build_position_profile(self.history(), 0)
        self.assertGreaterEqual(profile.walk_forward_samples, 24)
        self.assertIn(profile.max_miss_streak, range(profile.walk_forward_samples + 1))
        self.assertAlmostEqual(1.0, sum(profile.probabilities), places=9)
        self.assertEqual(6, len(profile.top6))
        self.assertEqual(7, len(profile.top7))

    def test_predict_exposes_evidence_and_structural_weights(self) -> None:
        result = predict(self.history())
        selected = result.selected
        self.assertEqual(10, len(result.positions))
        self.assertIsInstance(selected.evidence_passed, bool)
        self.assertGreaterEqual(selected.max_miss_streak, 0)
        self.assertTrue(set(STRUCTURAL_STRATEGIES).issubset(selected.strategy_weights))
        self.assertIn("012 路", result.analysis)
        self.assertIn("随机六码基准", result.analysis)


if __name__ == "__main__":
    unittest.main()
