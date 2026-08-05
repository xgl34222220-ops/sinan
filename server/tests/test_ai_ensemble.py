from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ai_ensemble import (
    _ReviewerResult,
    _anonymized_items,
    _anonymized_number_series,
    _anonymized_position_history,
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
        self.assertEqual(
            raw[-1]["values_by_candidate"]["A"],
            history[-1].numbers[9],
        )

    def test_anonymous_number_series_uses_candidate_labels_not_real_numbers(self) -> None:
        history = _history(30)
        mapping = {label: index for index, label in enumerate("JIHGFEDCBA")}
        series = _anonymized_number_series(history, position=0, mapping=mapping)

        self.assertEqual(len(series), 30)
        self.assertTrue(all(item["candidate_id"] in set("ABCDEFGHIJ") for item in series))
        self.assertTrue(all("number" not in item for item in series))

    def test_collapse_review_requires_six_consecutive_same_positions(self) -> None:
        self.assertFalse(needs_collapse_review([0, 0, 0, 0, 0], 0))
        self.assertTrue(needs_collapse_review([0, 0, 0, 0, 0, 0], 0))
        self.assertFalse(needs_collapse_review([0, 0, 1, 0, 0, 0], 0))

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
