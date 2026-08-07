from __future__ import annotations

import unittest

from app.fixed_target_bridge import (
    RANDOM_BASELINE,
    TARGET_LABEL,
    TARGET_NUMBERS,
    build_fixed_target_profiles,
)
from app.models import DrawModel


class FixedTargetBridgeTest(unittest.TestCase):
    def test_target_pool_maps_zero_to_ten(self) -> None:
        self.assertEqual(TARGET_LABEL, "235780")
        self.assertEqual(TARGET_NUMBERS, (2, 3, 5, 7, 8, 10))
        self.assertAlmostEqual(RANDOM_BASELINE, 0.60)

    def test_position_with_persistent_target_membership_ranks_first(self) -> None:
        target = list(TARGET_NUMBERS)
        history: list[DrawModel] = []
        for index in range(120):
            first = target[index % len(target)]
            remaining = [number for number in range(1, 11) if number != first]
            shift = index % len(remaining)
            rotated = remaining[shift:] + remaining[:shift]
            history.append(
                DrawModel(
                    lottery="xyft",
                    period=str(100000 + index),
                    numbers=[first, *rotated],
                )
            )
        profiles = build_fixed_target_profiles(history)
        best = max(profiles, key=lambda profile: profile.score)
        self.assertEqual(best.position, 0)
        self.assertGreater(best.target_probability, RANDOM_BASELINE)
        self.assertAlmostEqual(
            sum(best.exact_probabilities[number - 1] for number in TARGET_NUMBERS),
            best.target_probability,
            places=9,
        )


if __name__ == "__main__":
    unittest.main()
