from __future__ import annotations

import unittest

from app.forecast_quality import (
    position_quality_profile,
    recent_copy_diagnostics,
    regularize_recent_copy,
)
from app.models import DrawModel


def history(count: int = 120) -> list[DrawModel]:
    draws: list[DrawModel] = []
    for index in range(count):
        shift = index % 10
        numbers = list(range(1, 11))
        numbers = numbers[shift:] + numbers[:shift]
        draws.append(
            DrawModel(
                lottery="azxy10",
                period=str(21348000 + index),
                numbers=numbers,
                draw_time="",
                source="api68",
            )
        )
    return draws


class ForecastQualityTests(unittest.TestCase):
    def test_position_quality_uses_walk_forward_samples(self) -> None:
        profile = position_quality_profile(history(), 0)
        self.assertGreaterEqual(profile.walk_forward_samples, 12)
        self.assertGreater(profile.validation_score, 0)
        self.assertAlmostEqual(sum(profile.probabilities), 1.0)
        self.assertEqual(len(profile.top6), 6)

    def test_exact_latest_six_copy_is_detected_and_broken_on_weak_boundary(self) -> None:
        draws = history()
        latest_six = {draw.numbers[0] for draw in draws[-6:]}
        self.assertEqual(len(latest_six), 6)
        probabilities = [0.04] * 10
        for number in latest_six:
            probabilities[number - 1] = 0.14
        total = sum(probabilities)
        probabilities = [value / total for value in probabilities]
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
        self.assertTrue(recent_copy_diagnostics(ranked, draws, 0).exact_latest_six)
        adjusted, applied = regularize_recent_copy(probabilities, draws, 0)
        adjusted_ranked = sorted(range(10), key=adjusted.__getitem__, reverse=True)
        self.assertTrue(applied)
        self.assertNotEqual(
            {index + 1 for index in adjusted_ranked[:6]},
            latest_six,
        )
        self.assertAlmostEqual(sum(adjusted), 1.0)


if __name__ == "__main__":
    unittest.main()
