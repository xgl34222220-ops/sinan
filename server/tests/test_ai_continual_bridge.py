from __future__ import annotations

import math
import unittest

from app.ai_continual_bridge import (
    blend_position_scores,
    position_learning_payload,
    position_strategy_probabilities,
    position_strategy_weights,
)
from app.continual_learning import ContinualPositionProfile


def profile(
    position: int,
    *,
    hit_rate: float,
    loss: float,
    max_miss: int,
    score: float,
) -> ContinualPositionProfile:
    probabilities = [0.1] * 10
    return ContinualPositionProfile(
        position=position,
        probabilities=probabilities,
        top6=[1, 2, 3, 4, 5, 6],
        top7=[1, 2, 3, 4, 5, 6, 7],
        boundary_margin=0.01,
        walk_forward_samples=48,
        walk_forward_hits=round(hit_rate * 48),
        walk_forward_hit_rate=hit_rate,
        average_log_loss=loss,
        validation_score=score,
        excess_hit_rate=hit_rate - 0.60,
        max_miss_streak=max_miss,
        strategy_probabilities={"route012": probabilities},
        strategy_weights={"route012": 0.6, "universal_pool": 0.4},
    )


class AiContinualBridgeTest(unittest.TestCase):
    def profiles(self) -> tuple[ContinualPositionProfile, ...]:
        values = [
            profile(
                index,
                hit_rate=0.64 if index == 4 else 0.58,
                loss=2.20 if index == 4 else 2.42,
                max_miss=3 if index == 4 else 9,
                score=1.4 if index == 4 else 0.8,
            )
            for index in range(10)
        ]
        return tuple(values)

    def test_forward_evidence_can_block_extreme_weak_ai_choice(self) -> None:
        ai_scores = [0.01] * 10
        ai_scores[0] = 0.91
        blended = blend_position_scores(ai_scores, self.profiles())
        self.assertEqual(4, max(range(10), key=blended.__getitem__))
        self.assertAlmostEqual(1.0, sum(blended), places=9)

    def test_payload_contains_random_baseline_and_gate(self) -> None:
        payload = position_learning_payload(self.profiles()[4])
        self.assertTrue(payload["evidence_gate_passed"])
        self.assertEqual(48, payload["forward_samples"])
        self.assertGreater(payload["excess_over_random_top6"], 0)
        self.assertAlmostEqual(math.log(10.0), payload["uniform_log_loss_baseline"], places=5)
        self.assertEqual("route012", payload["leading_learned_strategies"][0]["strategy"])

    def test_without_valid_shape_scores_still_normalize(self) -> None:
        blended = blend_position_scores([2.0, 1.0], self.profiles())
        self.assertEqual(2, len(blended))
        self.assertAlmostEqual(1.0, sum(blended), places=9)

    def test_ai_reviewer_memory_is_namespaced_by_position(self) -> None:
        probabilities = {
            "ai_reviewer_1": [0.19, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09],
            "ai_reviewer_2": [0.09, 0.19, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09],
        }
        namespaced = position_strategy_probabilities(2, probabilities)
        self.assertEqual(
            {"ai_position_3:reviewer_1", "ai_position_3:reviewer_2"},
            set(namespaced),
        )
        self.assertTrue(all(name.startswith("ai_") for name in namespaced))
        weights = position_strategy_weights(
            2,
            probabilities,
            {
                "ai_position_3:reviewer_1": 0.8,
                "ai_position_3:reviewer_2": 0.2,
                "ai_position_7:reviewer_1": 1.0,
            },
        )
        self.assertAlmostEqual(0.8, weights["ai_position_3:reviewer_1"], places=9)
        self.assertAlmostEqual(0.2, weights["ai_position_3:reviewer_2"], places=9)
        self.assertAlmostEqual(1.0, sum(weights.values()), places=9)


if __name__ == "__main__":
    unittest.main()
