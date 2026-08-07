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
        return SimpleNamespace(scores=scores, analysis=f"首选{best + 1}", usage={})

    def test_consensus_is_diagnostic_only_and_normalized(self) -> None:
        reviews = [self.review(1), self.review(1), self.review(4, second=1)]
        scores, selected, ranking = guard._ai_consensus(reviews)
        self.assertEqual(1, selected)
        self.assertEqual(1, ranking[0])
        self.assertAlmostEqual(1.0, sum(scores), places=6)

    def test_recent_decisions_include_actual_number_and_do_not_force_rotation(self) -> None:
        history = [SimpleNamespace(lottery="xyft")]
        forecasts = [
            SimpleNamespace(source="ai", model="deepseek-v4-pro", target_period="103", position=1, top6_hit=False, actual_number=4),
            SimpleNamespace(source="ai", model="deepseek-v4-pro", target_period="102", position=1, top6_hit=False, actual_number=6),
            SimpleNamespace(source="native", model="tianji-native-cloud-v1", target_period="101", position=7, top6_hit=False, actual_number=4),
        ]
        with patch.object(guard.database, "list_forecasts", return_value=forecasts):
            decisions = guard._recent_ai_decisions(history, "deepseek-v4-pro")
        self.assertEqual(
            [
                {"target_period": "103", "selected_position": 2, "actual_number": 4, "hit_fixed_235780": False},
                {"target_period": "102", "selected_position": 2, "actual_number": 6, "hit_fixed_235780": False},
            ],
            decisions,
        )

    def test_trend_evidence_contains_real_numbers_and_all_windows(self) -> None:
        history = []
        for index in range(240):
            numbers = list(range(1, 11))
            shift = index % 10
            numbers = numbers[shift:] + numbers[:shift]
            history.append(SimpleNamespace(period=str(index), numbers=numbers))
        profiles = tuple(
            SimpleNamespace(
                target_probability=0.60,
                validation_samples=120,
                validation_hit_rate=0.60,
                average_log_loss=0.67,
                average_brier=0.24,
                max_miss_streak=4,
                current_miss_streak=0,
            )
            for _ in range(10)
        )
        with patch.object(guard.fixed_target_bridge, "_canonical", return_value=history):
            evidence = guard._trend_evidence(history, profiles)
        self.assertEqual(10, len(evidence))
        first = evidence[0]
        self.assertEqual({"24", "60", "120", "240"}, set(first["window_target_hit_rates"]))
        self.assertEqual(24, len(first["recent_actual_numbers_newest_to_oldest"]))
        self.assertEqual(60, len(first["recent_target_hits_newest_to_oldest"]))
        self.assertIn("rate24_minus_rate60", first["trend_deltas"])
        self.assertIn("successor_number_counts_1_to_10", first["transitions"])

    def test_reviewer_receives_full_actual_trend_and_specialized_role(self) -> None:
        captured: dict = {}
        evidence = [{"position": index + 1, "signal": index} for index in range(10)]
        mapping = {f"N{index + 1:02d}": index for index in range(10)}
        by_actual = {index: f"N{index + 1:02d}" for index in range(10)}
        reviewer_mapping = {chr(65 + index): index for index in range(10)}

        def fake_call_json(config, **kwargs):
            captured.update(kwargs)
            return {"scores": {chr(65 + i): 1 for i in range(10)}, "selected": "A", "analysis": "测试"}

        with patch.object(guard, "_trend_evidence", return_value=evidence), patch.object(
            guard, "_full_trend_history", return_value={"actual_numbers_by_candidate_oldest_to_newest": {"N01": [2, 4, 7]}}
        ), patch.object(
            guard.ai_ensemble,
            "_shared_anonymized_items",
            return_value=([{"evidence_id": f"N{i + 1:02d}"} for i in range(10)], mapping, by_actual),
        ), patch.object(
            guard.ai_ensemble,
            "_anonymized_items",
            return_value=([{"candidate_id": chr(65 + i)} for i in range(10)], reviewer_mapping),
        ), patch.object(
            guard.fixed_target_bridge,
            "_canonical",
            return_value=[SimpleNamespace(period="99")],
        ), patch.object(
            guard.ai_ensemble,
            "_reviewer_aliases",
            return_value={chr(65 + i): f"N{i + 1:02d}" for i in range(10)},
        ), patch.object(
            guard.ai_ensemble, "_call_json", side_effect=fake_call_json
        ), patch.object(
            guard.ai_ensemble,
            "_parse_label_scores",
            return_value=SimpleNamespace(scores=[0.1] * 10, analysis="测试", usage={}),
        ):
            guard._autonomous_review(
                SimpleNamespace(model="deepseek-v4-pro"),
                history=[SimpleNamespace(period="99")],
                profiles=tuple(SimpleNamespace() for _ in range(10)),
                target_period="100",
                reviewer=0,
                recent_decisions=[{"target_period": "99", "selected_position": 1, "actual_number": 4, "hit_fixed_235780": False}],
            )

        shared = captured["shared_payload"]
        self.assertEqual("full_actual_number_trend_plus_target_membership_and_forward_validation", shared["evidence_mode"])
        self.assertIn("neutral_full_trend_history", shared)
        self.assertIn("真实1至10号码序列", captured["system_prompt"])
        self.assertEqual("short_term_trend", captured["reviewer_payload"]["reviewer_role"])

    def test_final_judge_receives_three_specialists_and_has_no_hard_rotation(self) -> None:
        captured: dict = {}
        evidence = [{"position": index + 1, "signal": index} for index in range(10)]
        judge_mapping = {chr(65 + index): index for index in range(10)}

        def fake_call_json(config, **kwargs):
            captured.update(kwargs)
            return {"scores": {chr(65 + i): (10 if i == 4 else 1) for i in range(10)}, "selected": "E", "analysis": "走势转强"}

        with patch.object(guard, "_trend_evidence", return_value=evidence), patch.object(
            guard.ai_ensemble,
            "_anonymized_items",
            return_value=([{"candidate_id": chr(65 + i), "evidence": {}} for i in range(10)], judge_mapping),
        ), patch.object(guard.ai_ensemble, "_call_json", side_effect=fake_call_json), patch.object(
            guard.ai_ensemble,
            "_parse_label_scores",
            return_value=SimpleNamespace(scores=[0.01, 0.01, 0.01, 0.01, 0.91, 0.01, 0.01, 0.01, 0.01, 0.01], analysis="走势转强", usage={}),
        ):
            result = guard._final_judge(
                SimpleNamespace(model="deepseek-v4-pro"),
                history=[SimpleNamespace(period="99")],
                profiles=tuple(SimpleNamespace() for _ in range(10)),
                target_period="100",
                reviews=[self.review(1), self.review(2), self.review(3)],
                recent_decisions=[],
            )
        self.assertEqual(4, max(range(10), key=lambda i: result.scores[i]))
        self.assertEqual(3, len(captured["shared_payload"]["specialist_reviews"]))
        self.assertIn("没有任何轮换、禁选、冷却", captured["system_prompt"])


if __name__ == "__main__":
    unittest.main()
