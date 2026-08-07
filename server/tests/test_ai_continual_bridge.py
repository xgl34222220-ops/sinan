from __future__ import annotations

import math
from types import SimpleNamespace
import unittest

from app.ai_continual_bridge import (
    _POSITION_PROFILES,
    _TaggedPositionReview,
    _aggregate_with_position_learning,
    _hybrid_strategy_weights,
    blend_position_scores,
    position_learning_payload,
    position_strategy_probabilities,
    position_strategy_weights,
    statistical_prior_weight,
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

    @staticmethod
    def reviewer_probabilities() -> dict[str, list[float]]:
        return {
            "ai_reviewer_1": [0.19, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09],
            "ai_reviewer_2": [0.09, 0.19, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09, 0.09],
        }

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
        self.assertGreaterEqual(payload["number_statistical_prior_seed_weight"], 0.40)

    def test_without_valid_shape_scores_still_normalize(self) -> None:
        blended = blend_position_scores([2.0, 1.0], self.profiles())
        self.assertEqual(2, len(blended))
        self.assertAlmostEqual(1.0, sum(blended), places=9)

    def test_ai_reviewer_memory_is_namespaced_by_position_and_v2(self) -> None:
        probabilities = self.reviewer_probabilities()
        namespaced = position_strategy_probabilities(2, probabilities)
        self.assertEqual(
            {"ai_v2_position_3:reviewer_1", "ai_v2_position_3:reviewer_2"},
            set(namespaced),
        )
        weights = position_strategy_weights(
            2,
            probabilities,
            {
                "ai_v2_position_3:reviewer_1": 0.8,
                "ai_v2_position_3:reviewer_2": 0.2,
                "ai_v2_position_7:reviewer_1": 1.0,
            },
        )
        self.assertAlmostEqual(0.8, weights["ai_v2_position_3:reviewer_1"], places=9)
        self.assertAlmostEqual(0.2, weights["ai_v2_position_3:reviewer_2"], places=9)
        self.assertAlmostEqual(1.0, sum(weights.values()), places=9)

    def test_number_aggregate_is_never_polluted_by_position_profiles(self) -> None:
        # Old behavior silently blended any ten-value vector with position
        # profiles. Number scores are also ten values, so a strong fifth
        # position could corrupt a number review whose best number is 1.
        number_review = SimpleNamespace(
            scores=[0.91, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01]
        )
        token = _POSITION_PROFILES.set(self.profiles())
        try:
            aggregated = _aggregate_with_position_learning([number_review])
        finally:
            _POSITION_PROFILES.reset(token)
        self.assertEqual(0, max(range(10), key=aggregated.__getitem__))
        self.assertAlmostEqual(1.0, sum(aggregated), places=9)

    def test_tagged_position_aggregate_still_receives_forward_calibration(self) -> None:
        position_review = _TaggedPositionReview(
            scores=[0.91, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
            analysis="test",
            usage={},
        )
        token = _POSITION_PROFILES.set(self.profiles())
        try:
            aggregated = _aggregate_with_position_learning([position_review])
        finally:
            _POSITION_PROFILES.reset(token)
        self.assertEqual(4, max(range(10), key=aggregated.__getitem__))

    def test_strong_forward_profile_seeds_number_statistical_prior(self) -> None:
        probabilities = self.reviewer_probabilities()
        selected = self.profiles()[4]
        combined = position_strategy_probabilities(
            4,
            probabilities,
            selected.probabilities,
        )
        weights = _hybrid_strategy_weights(4, combined, None, selected)
        statistical_name = "ai_v2_position_5:forward_statistical_prior"
        self.assertIn(statistical_name, combined)
        self.assertGreaterEqual(statistical_prior_weight(selected), 0.40)
        self.assertGreaterEqual(weights[statistical_name], 0.40)
        self.assertAlmostEqual(1.0, sum(weights.values()), places=9)

    def test_v2_hybrid_ignores_legacy_strategy_weights(self) -> None:
        probabilities = self.reviewer_probabilities()
        selected = self.profiles()[4]
        combined = position_strategy_probabilities(4, probabilities, selected.probabilities)
        weights = _hybrid_strategy_weights(
            4,
            combined,
            {
                "ai_reviewer_1": 0.99,
                "ai_position_5:reviewer_1": 0.99,
                "ai_fixed_235780_position_5": 0.99,
            },
            selected,
        )
        statistical_name = "ai_v2_position_5:forward_statistical_prior"
        self.assertGreaterEqual(weights[statistical_name], 0.40)
        self.assertAlmostEqual(
            weights["ai_v2_position_5:reviewer_1"],
            weights["ai_v2_position_5:reviewer_2"],
            places=9,
        )

    def test_settled_v2_learning_can_downweight_statistical_prior(self) -> None:
        probabilities = self.reviewer_probabilities()
        selected = self.profiles()[4]
        combined = position_strategy_probabilities(4, probabilities, selected.probabilities)
        learned = {
            "ai_v2_position_5:reviewer_1": 0.80,
            "ai_v2_position_5:reviewer_2": 0.10,
            "ai_v2_position_5:forward_statistical_prior": 0.10,
        }
        weights = _hybrid_strategy_weights(4, combined, learned, selected)
        self.assertAlmostEqual(
            0.10,
            weights["ai_v2_position_5:forward_statistical_prior"],
            places=9,
        )
        self.assertAlmostEqual(1.0, sum(weights.values()), places=9)


if __name__ == "__main__":
    unittest.main()
