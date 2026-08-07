from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ai_ensemble import (
    _ReviewerResult,
    _anonymized_items,
    _number_review,
    _position_review,
    _run_prefix_cached,
    _usage_from_response,
    analyze_ensemble,
    build_position_evidence,
)
from app.models import DrawModel
from app.runtime_config import RuntimeAiConfig


def history(count: int = 120) -> list[DrawModel]:
    values: list[DrawModel] = []
    for index in range(count):
        numbers = list(range(1, 11))
        shift = index % 10
        numbers = numbers[shift:] + numbers[:shift]
        values.append(
            DrawModel(
                lottery="azxy10",
                period=str(21348000 + index),
                numbers=numbers,
            )
        )
    return values


def config() -> RuntimeAiConfig:
    return RuntimeAiConfig(
        enabled=True,
        endpoint="https://api.deepseek.com/chat/completions",
        model="deepseek-v4-pro",
        api_key="secret",
        timeout_seconds=60,
    )


def labeled_scores() -> dict[str, int]:
    return {label: index for index, label in enumerate("ABCDEFGHIJ", start=1)}


class PrefixCacheTests(unittest.TestCase):
    @patch("app.ai_ensemble._call_json")
    def test_position_reviewers_share_neutral_prefix_and_preserve_original_mapping(self, call_json: object) -> None:
        calls: list[dict[str, object]] = []

        def fake_call(*args: object, **kwargs: object) -> dict[str, object]:
            calls.append(dict(kwargs))
            return {
                "scores": labeled_scores(),
                "analysis": "独立评审",
                "_tianji_usage": {"request_count": 1},
            }

        call_json.side_effect = fake_call
        draws = history()
        evidence = build_position_evidence(draws)
        results = []
        for reviewer in (0, 1):
            results.append(
                _position_review(
                    config(),
                    history=draws,
                    evidence=evidence,
                    target_period="21348120",
                    trained_through_period="21348119",
                    reviewer=reviewer,
                    challenge=False,
                )
            )
        self.assertEqual(calls[0]["system_prompt"], calls[1]["system_prompt"])
        self.assertEqual(calls[0]["shared_payload"], calls[1]["shared_payload"])
        tail0 = calls[0]["reviewer_payload"]
        tail1 = calls[1]["reviewer_payload"]
        self.assertIsInstance(tail0, dict)
        self.assertIsInstance(tail1, dict)
        assert isinstance(tail0, dict) and isinstance(tail1, dict)
        self.assertNotEqual(
            tail0["candidate_aliases_A_to_J"],
            tail1["candidate_aliases_A_to_J"],
        )
        for reviewer, result in enumerate(results):
            _, original_mapping = _anonymized_items(
                evidence,
                target_period="21348120",
                phase="position",
                reviewer=reviewer,
            )
            for label, actual_index in original_mapping.items():
                self.assertAlmostEqual(
                    result.scores[actual_index],
                    labeled_scores()[label] / 55.0,
                )

    @patch("app.ai_ensemble._call_json")
    def test_number_reviewers_share_neutral_prefix_but_keep_independent_aliases(self, call_json: object) -> None:
        calls: list[dict[str, object]] = []

        def fake_call(*args: object, **kwargs: object) -> dict[str, object]:
            calls.append(dict(kwargs))
            return {
                "scores": labeled_scores(),
                "analysis": "号码评审",
                "_tianji_usage": {"request_count": 1},
            }

        call_json.side_effect = fake_call
        draws = history()
        for reviewer in (0, 1):
            _number_review(
                config(),
                history=draws,
                position=0,
                target_period="21348120",
                trained_through_period="21348119",
                reviewer=reviewer,
                mask_recent=0,
            )
        self.assertEqual(calls[0]["system_prompt"], calls[1]["system_prompt"])
        self.assertEqual(calls[0]["shared_payload"], calls[1]["shared_payload"])
        tail0 = calls[0]["reviewer_payload"]
        tail1 = calls[1]["reviewer_payload"]
        assert isinstance(tail0, dict) and isinstance(tail1, dict)
        self.assertNotEqual(
            tail0["candidate_aliases_A_to_J"],
            tail1["candidate_aliases_A_to_J"],
        )

    def test_first_reviewer_finishes_before_cache_candidates(self) -> None:
        order: list[int] = []

        def task(reviewer: int) -> _ReviewerResult:
            order.append(reviewer)
            return _ReviewerResult(scores=[0.1] * 10, analysis="")

        results = _run_prefix_cached(3, task)
        self.assertEqual(len(results), 3)
        self.assertEqual(order[0], 0)
        self.assertEqual(set(order[1:]), {1, 2})

    def test_deepseek_usage_fields_are_preserved(self) -> None:
        usage = _usage_from_response(
            {
                "usage": {
                    "prompt_tokens": 1000,
                    "prompt_cache_hit_tokens": 800,
                    "prompt_cache_miss_tokens": 200,
                    "completion_tokens": 50,
                    "total_tokens": 1050,
                    "completion_tokens_details": {"reasoning_tokens": 20},
                }
            }
        )
        self.assertEqual(usage["prompt_cache_hit_tokens"], 800)
        self.assertEqual(usage["prompt_cache_miss_tokens"], 200)
        self.assertEqual(usage["reasoning_tokens"], 20)

    @patch("app.ai_position_autonomy_guard._autonomous_review")
    def test_fixed_target_ensemble_aggregates_usage_without_number_reviewers(
        self,
        target_review: object,
    ) -> None:
        target_review.side_effect = lambda *args, **kwargs: _ReviewerResult(
            scores=[0.1] * 10,
            analysis="固定目标名次",
            usage={
                "request_count": 1,
                "prompt_tokens": 100,
                "prompt_cache_hit_tokens": 60,
                "prompt_cache_miss_tokens": 40,
                "completion_tokens": 10,
                "reasoning_tokens": 2,
            },
        )
        result = analyze_ensemble(history(), "21348120", config())
        self.assertEqual(result.position_reviewers, 3)
        self.assertEqual(result.number_reviewers, 0)
        self.assertEqual(result.request_count, 3)
        self.assertEqual(result.prompt_cache_hit_tokens, 180)
        self.assertEqual(result.prompt_cache_miss_tokens, 120)
        self.assertAlmostEqual(result.cache_hit_rate, 0.60)


if __name__ == "__main__":
    unittest.main()
