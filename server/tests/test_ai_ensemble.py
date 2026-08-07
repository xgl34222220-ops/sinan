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

    def test_collapse_review_starts_after_three_consecutive_same_positions(self) -> None:
        self.assertFalse(needs_collapse_review([0, 0], 0))
        self.assertTrue(needs_collapse_review([0, 0, 0], 0))
        self.assertFalse(needs_collapse_review([0, 0, 1, 0], 0))

    @patch("app.ai_ensemble._number_review")
    @patch("app.ai_ensemble._position_review")
    def test_formal_ai_prediction_generates_dynamic_six_numbers(
        self,
        position_review: object,
        number_review: object,
    ) -> None:
        position_scores = [0.01] * 10
        position_scores[0] = 0.91
        position_review.side_effect = lambda *args, **kwargs: _ReviewerResult(
            scores=position_scores,
            analysis="动态名次评审",
        )
        dynamic_order = [1, 4, 6, 9, 10, 2, 3, 5, 7, 8]
        number_review.side_effect = lambda *args, **kwargs: _ReviewerResult(
            scores=_scores_for_order(dynamic_order),
            analysis="动态号码评审",
        )

        result = analyze_ensemble(_history(), "21348120", _config())
        self.assertEqual(result.position, 0)
        self.assertEqual(result.top6, dynamic_order[:6])
        self.assertNotEqual(result.top6, [2, 3, 5, 7, 8, 10])
        self.assertGreaterEqual(result.number_reviewers, 2)
        self.assertTrue(result.strategy_probabilities)
        self.assertTrue(
            any("forward_statistical_prior" in name for name in result.strategy_probabilities)
        )
        self.assertIn("动态混合", result.analysis)

    @patch("app.ai_ensemble._number_review")
    @patch("app.ai_ensemble._position_review")
    def test_dynamic_ai_is_allowed_to_agree_with_any_six_number_set(
        self,
        position_review: object,
        number_review: object,
    ) -> None:
        position_scores = [0.01] * 10
        position_scores[0] = 0.91
        position_review.side_effect = lambda *args, **kwargs: _ReviewerResult(
            scores=position_scores,
            analysis="独立名次评审",
        )
        agreed_order = [2, 3, 5, 7, 8, 10, 1, 4, 6, 9]
        number_review.side_effect = lambda *args, **kwargs: _ReviewerResult(
            scores=_scores_for_order(agreed_order),
            analysis="独立号码评审",
        )

        result = analyze_ensemble(_history(), "21348120", _config())
        self.assertEqual(result.top6, agreed_order[:6])
        self.assertGreaterEqual(result.number_reviewers, 2)
        self.assertIn("不会为了与本地不同而强制改号", result.analysis)

    @patch("app.ai_ensemble._position_review", side_effect=RuntimeError("provider down"))
    def test_provider_failure_does_not_forge_a_statistical_ai_prediction(
        self,
        _position_review: object,
    ) -> None:
        with self.assertRaisesRegex(RuntimeError, "全部AI评审失败"):
            analyze_ensemble(_history(), "21348120", _config())


if __name__ == "__main__":
    unittest.main()
