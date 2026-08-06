from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ai_ensemble import (
    _ReviewerResult,
    _anonymized_items,
    _anonymized_number_series,
    _anonymized_position_history,
    _blend_probabilities,
    _number_evidence,
    _number_review,
    analyze_ensemble,
    build_position_evidence,
    needs_collapse_review,
)
from app.models import DrawModel
from app.runtime_config import RuntimeAiConfig


def _history(count: int = 120) -> list[DrawModel]:
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


def _config() -> RuntimeAiConfig:
    return RuntimeAiConfig(
        enabled=True,
        endpoint="https://example.com/v1/chat/completions",
        model="test-ai",
        api_key="secret",
        timeout_seconds=60,
    )


def _scores_for_order(order: list[int]) -> list[float]:
    scores = [0.0] * 10
    for weight, number in enumerate(reversed(order), start=1):
        scores[number - 1] = float(weight)
    return scores


class AiEnsembleTests(unittest.TestCase):
    def test_position_evidence_contains_all_ten_api_positions(self) -> None:
        evidence = build_position_evidence(_history())
        self.assertEqual(len(evidence), 10)
        self.assertEqual([item["position"] for item in evidence], list(range(1, 11)))
        for item in evidence:
            self.assertEqual(len(item["count_120_by_number_1_to_10"]), 10)
            self.assertEqual(len(item["omission_by_number_1_to_10"]), 10)

    def test_anonymization_hides_real_position_and_number_identity(self) -> None:
        items = [
            {"position": index + 1, "number": index + 1, "signal": index}
            for index in range(10)
        ]
        candidates, mapping = _anonymized_items(
            items,
            target_period="21348120",
            phase="position",
            reviewer=0,
        )
        self.assertEqual(set(mapping), set("ABCDEFGHIJ"))
        self.assertEqual(sorted(mapping.values()), list(range(10)))
        self.assertTrue(all("position" not in item["evidence"] for item in candidates))
        self.assertTrue(all("number" not in item["evidence"] for item in candidates))

    def test_anonymous_raw_history_keeps_periods_but_hides_column_order(self) -> None:
        history = _history(30)
        mapping = {label: 9 - index for index, label in enumerate("ABCDEFGHIJ")}
        raw = _anonymized_position_history(history, mapping)
        self.assertEqual(raw[-1]["period"], history[-1].period)
        self.assertEqual(set(raw[-1]["values_by_candidate"]), set("ABCDEFGHIJ"))
        self.assertEqual(raw[-1]["values_by_candidate"]["A"], history[-1].numbers[9])

    def test_number_sequence_keeps_full_order_but_only_uses_labels(self) -> None:
        history = _history()
        mapping = {label: index for index, label in enumerate("ABCDEFGHIJ")}
        series = _anonymized_number_series(history, position=0, mapping=mapping)
        self.assertEqual(len(series), 120)
        self.assertEqual(series[0]["candidate_id"], "A")
        self.assertEqual(series[-1]["candidate_id"], "J")
        self.assertTrue(all(set(item) == {"period", "candidate_id"} for item in series))
        self.assertTrue(all(item["candidate_id"] in set("ABCDEFGHIJ") for item in series))
        masked = _anonymized_number_series(
            history,
            position=0,
            mapping=mapping,
            mask_recent=7,
        )
        self.assertEqual(len(masked), 113)
        self.assertEqual(masked[-1]["candidate_id"], "C")

    def test_number_evidence_does_not_leak_recent_sequence_or_current_number(self) -> None:
        evidence = _number_evidence(_history(), position=0)
        self.assertEqual(len(evidence), 10)
        for item in evidence:
            self.assertNotIn("latest_16_newest_to_oldest", item)
            self.assertNotIn("current_number", item)
            self.assertNotIn("latest_sequence", item)
            self.assertIn("count_12", item)
            self.assertIn("transition_rate", item)

    @patch("app.ai_ensemble._call_json")
    def test_number_review_sends_full_anonymous_sequence_and_aggregates(self, call_json: object) -> None:
        captured: dict[str, object] = {}

        def fake_call(*args: object, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {
                "scores": {label: 1 for label in "ABCDEFGHIJ"},
                "analysis": "完整匿名时序评审",
            }

        call_json.side_effect = fake_call
        _number_review(
            _config(),
            history=_history(),
            position=0,
            target_period="21348120",
            trained_through_period="21348119",
            reviewer=0,
        )
        shared = captured["shared_payload"]
        reviewer_tail = captured["reviewer_payload"]
        self.assertIsInstance(shared, dict)
        self.assertIsInstance(reviewer_tail, dict)
        assert isinstance(shared, dict)
        assert isinstance(reviewer_tail, dict)
        self.assertEqual(
            shared["evidence_mode"],
            "neutral_anonymous_full_sequence_plus_aggregates",
        )
        self.assertEqual(shared["history_order"], "oldest_to_newest")
        self.assertEqual(len(shared["neutral_history"]), 120)
        neutral_ids = {f"N{index:02d}" for index in range(1, 11)}
        self.assertTrue(
            all(
                item["candidate_id"] in neutral_ids
                and set(item) == {"period", "candidate_id"}
                for item in shared["neutral_history"]
            )
        )
        for candidate in shared["neutral_candidates"]:
            self.assertNotIn("number", candidate["evidence"])
            self.assertNotIn("current_number", candidate["evidence"])
            self.assertNotIn("latest_16_newest_to_oldest", candidate["evidence"])
        aliases = reviewer_tail["candidate_aliases_A_to_J"]
        self.assertEqual(set(aliases), set("ABCDEFGHIJ"))
        self.assertEqual(set(aliases.values()), neutral_ids)

    def test_blend_probabilities_keeps_both_ai_reviews(self) -> None:
        primary = _scores_for_order([4, 5, 6, 7, 8, 9, 10, 1, 2, 3])
        holdout = _scores_for_order([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        blended = _blend_probabilities(primary, holdout)
        self.assertAlmostEqual(sum(blended), 1.0)
        self.assertNotEqual(blended, primary)
        self.assertNotEqual(blended, holdout)

    def test_collapse_review_requires_six_consecutive_same_positions(self) -> None:
        self.assertFalse(needs_collapse_review([0, 0, 0, 0, 0], 0))
        self.assertTrue(needs_collapse_review([0, 0, 0, 0, 0, 0], 0))
        self.assertFalse(needs_collapse_review([0, 0, 1, 0, 0, 0], 0))

    @patch("app.ai_ensemble._number_review")
    @patch("app.ai_ensemble._position_review")
    def test_recent_seven_copy_adds_holdout_ai_review_and_blends_results(
        self,
        position_review: object,
        number_review: object,
    ) -> None:
        position_scores = [0.02] * 10
        position_scores[0] = 0.82
        initial_order = [4, 5, 6, 7, 8, 9, 10, 1, 2, 3]
        holdout_order = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        masks: list[int] = []
        position_review.side_effect = lambda *args, **kwargs: _ReviewerResult(
            scores=position_scores,
            analysis="匿名名次评审",
        )

        def fake_number_review(*args: object, **kwargs: object) -> _ReviewerResult:
            mask_recent = int(kwargs.get("mask_recent", 0))
            masks.append(mask_recent)
            return _ReviewerResult(
                scores=_scores_for_order(holdout_order if mask_recent else initial_order),
                analysis="匿名留出评审" if mask_recent else "完整匿名历史评审",
            )

        number_review.side_effect = fake_number_review
        result = analyze_ensemble(_history(), "21348120", _config())
        self.assertTrue(result.recent_copy_reviewed)
        self.assertEqual(masks.count(0), 2)
        self.assertEqual(masks.count(7), 2)
        self.assertEqual(result.number_reviewers, 4)
        self.assertNotEqual(result.top7, initial_order[:7])
        self.assertIn("完整历史评审与留出评审加权汇总", result.analysis)
        self.assertIn("保留完整历史先后顺序", result.risk_note)

    @patch("app.ai_ensemble._number_review")
    @patch("app.ai_ensemble._position_review")
    def test_final_prediction_is_aggregated_from_ai_reviews_only(
        self,
        position_review: object,
        number_review: object,
    ) -> None:
        position_scores = [0.02] * 10
        position_scores[3] = 0.82
        number_scores = [0.03] * 10
        number_scores[7] = 0.73
        position_review.side_effect = lambda *args, **kwargs: _ReviewerResult(
            scores=position_scores,
            analysis="匿名名次评审",
        )
        number_review.side_effect = lambda *args, **kwargs: _ReviewerResult(
            scores=number_scores,
            analysis="匿名号码评审",
        )
        result = analyze_ensemble(
            _history(),
            "21348120",
            _config(),
            recent_positions=[3, 3, 3, 3, 3, 3],
        )
        self.assertEqual(result.position, 3)
        self.assertEqual(result.top6[0], 8)
        self.assertTrue(result.collapse_reviewed)
        self.assertIn("AI多轮", result.risk_note)
        self.assertIn("未人为强制轮换", result.analysis)

    @patch("app.ai_ensemble._position_review", side_effect=RuntimeError("provider down"))
    def test_provider_failure_does_not_forge_a_statistical_ai_prediction(
        self,
        _position_review: object,
    ) -> None:
        with self.assertRaisesRegex(RuntimeError, "全部AI评审失败"):
            analyze_ensemble(_history(), "21348120", _config())


if __name__ == "__main__":
    unittest.main()
