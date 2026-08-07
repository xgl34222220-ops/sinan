from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import ai_position_autonomy_guard as guard


class AiPositionAutonomyGuardTest(unittest.TestCase):
    def review(self, best: int, second: int | None = None) -> SimpleNamespace:
        scores = [0.01] * 10
        scores[best] = 0.80
        if second is not None:
            scores[second] = 0.15
        return SimpleNamespace(scores=scores, analysis=f"首选{best + 1}")

    def test_final_position_is_ai_consensus_without_math_or_cooldown_override(self) -> None:
        reviews = [self.review(1), self.review(1), self.review(4, second=1)]
        scores, selected, ranking = guard._ai_consensus(reviews)
        self.assertEqual(1, selected)
        self.assertEqual(1, ranking[0])
        self.assertAlmostEqual(1.0, sum(scores), places=6)

    def test_ai_is_allowed_to_repeat_same_position_when_its_evidence_still_wins(self) -> None:
        reviews = [self.review(1), self.review(1), self.review(1)]
        _scores, selected, _ranking = guard._ai_consensus(reviews)
        self.assertEqual(1, selected)

    def test_recent_decisions_are_evidence_not_a_forced_rotation_rule(self) -> None:
        history = [SimpleNamespace(lottery="xyft")]
        forecasts = [
            SimpleNamespace(
                source="ai",
                model="deepseek-v4-pro",
                target_period="103",
                position=1,
                top6_hit=False,
                actual_number=4,
            ),
            SimpleNamespace(
                source="ai",
                model="deepseek-v4-pro",
                target_period="102",
                position=1,
                top6_hit=False,
                actual_number=6,
            ),
            SimpleNamespace(
                source="native",
                model="tianji-native-cloud-v1",
                target_period="101",
                position=7,
                top6_hit=False,
                actual_number=4,
            ),
        ]
        with patch.object(guard.database, "list_forecasts", return_value=forecasts):
            decisions = guard._recent_ai_decisions(history, "deepseek-v4-pro")
        self.assertEqual(
            [
                {"target_period": "103", "selected_position": 2, "hit_fixed_235780": False},
                {"target_period": "102", "selected_position": 2, "hit_fixed_235780": False},
            ],
            decisions,
        )

    def test_reviewer_prompt_receives_ai_own_settled_history_and_forbids_hard_rotation(self) -> None:
        profile = SimpleNamespace(position=0)
        captured: dict = {}

        def fake_call_json(config, **kwargs):
            captured.update(kwargs)
            return {"scores": {chr(65 + i): 1 for i in range(10)}, "selected": "A", "analysis": "测试"}

        with patch.object(
            guard.fixed_target_bridge,
            "_profile_evidence",
            return_value={"position": 1},
        ), patch.object(
            guard.ai_ensemble,
            "_shared_anonymized_items",
            return_value=([{"id": "N0"}], {"N0": 0}, {0: "N0"}),
        ), patch.object(
            guard.ai_ensemble,
            "_anonymized_items",
            return_value=([{"id": "A"}], {"A": 0}),
        ), patch.object(
            guard.fixed_target_bridge,
            "_canonical",
            return_value=[SimpleNamespace(period="99")],
        ), patch.object(
            guard.fixed_target_bridge,
            "_target_membership_history",
            return_value=[{"period": "99", "target_hit_by_candidate": {"N0": 1}}],
        ), patch.object(
            guard.ai_ensemble,
            "_reviewer_aliases",
            return_value={"A": "N0"},
        ), patch.object(
            guard.ai_ensemble,
            "_call_json",
            side_effect=fake_call_json,
        ), patch.object(
            guard.ai_ensemble,
            "_parse_label_scores",
            return_value=SimpleNamespace(scores=[0.1] * 10, analysis="测试"),
        ):
            guard._autonomous_review(
                SimpleNamespace(model="deepseek-v4-pro"),
                history=[SimpleNamespace(period="99")],
                profiles=(profile,),
                target_period="100",
                reviewer=0,
                recent_decisions=[
                    {"target_period": "99", "selected_position": 1, "hit_fixed_235780": False}
                ],
            )

        self.assertIn("recent_ai_decision_outcomes", captured["shared_payload"])
        self.assertIn("不使用任何人工轮换", captured["system_prompt"])
        self.assertIn("也允许继续选同一位置", captured["system_prompt"])
        self.assertIn("不要机械轮换", captured["reviewer_payload"]["review_instruction"])


if __name__ == "__main__":
    unittest.main()
