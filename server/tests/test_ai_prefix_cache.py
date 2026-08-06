from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ai_ensemble import (
    _ReviewerResult,
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


class PrefixCacheTests(unittest.TestCase):
    @patch("app.ai_ensemble._call_json")
    def test_position_reviewers_share_large_prefix_but_keep_independent_tail(self, call_json: object) -> None:
        calls: list[dict[str, object]] = []

        def fake_call(*args: object, **kwargs: object) -> dict[str, object]:
            calls.append(dict(kwargs))
            return {
                "scores": {label: 1 for label in "ABCDEFGHIJ"},
                "analysis": "独立评审",
                "_tianji_usage": {"request_count": 1},
            }

        call_json.side_effect = fake_call
        evidence = build_position_evidence(history())
        for reviewer in (0, 1):
            _position_review(
                config(),
                history=history(),
                evidence=evidence,
                target_period="21348120",
                trained_through_period="21348119",
                reviewer=reviewer,
                challenge=False,
            )
        self.assertEqual(calls[0]["system_prompt"], calls[1]["system_prompt"])
        self.assertEqual(calls[0]["shared_payload"], calls[1]["shared_payload"])
        self.assertNotEqual(calls[0]["reviewer_payload"], calls[1]["reviewer_payload"])
        shared = calls[0]["shared_payload"]
        self.assertIsInstance(shared, dict)
        assert isinstance(shared, dict)
        self.assertNotIn("reviewer", shared)
        self.assertEqual(len(shared["anonymous_raw_draws"]), 120)

    def test_first_two_reviewers_finish_before_cache_candidate(self) -> None:
        order: list[int] = []

        def task(reviewer: int) -> _ReviewerResult:
            order.append(reviewer)
            return _ReviewerResult(scores=[0.1] * 10, analysis="")

        results = _run_prefix_cached(3, task)
        self.assertEqual(len(results), 3)
        self.assertEqual(order[:2], [0, 1])
        self.assertEqual(order[2], 2)

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

    @patch("app.ai_ensemble._number_review")
    @patch("app.ai_ensemble._position_review")
    def test_ensemble_aggregates_usage_without_changing_reviewer_count(
        self,
        position_review: object,
        number_review: object,
    ) -> None:
        position_scores = [0.1] * 10
        number_scores = [0.1] * 10
        position_review.side_effect = lambda *args, **kwargs: _ReviewerResult(
            scores=position_scores,
            analysis="名次",
            usage={
                "request_count": 1,
                "prompt_tokens": 100,
                "prompt_cache_hit_tokens": 60,
                "prompt_cache_miss_tokens": 40,
                "completion_tokens": 10,
                "reasoning_tokens": 2,
            },
        )
        number_review.side_effect = lambda *args, **kwargs: _ReviewerResult(
            scores=number_scores,
            analysis="号码",
            usage={
                "request_count": 1,
                "prompt_tokens": 50,
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": 50,
                "completion_tokens": 5,
                "reasoning_tokens": 1,
            },
        )
        result = analyze_ensemble(history(), "21348120", config())
        self.assertEqual(result.position_reviewers, 3)
        self.assertEqual(result.number_reviewers, 2)
        self.assertEqual(result.request_count, 5)
        self.assertEqual(result.prompt_cache_hit_tokens, 180)
        self.assertEqual(result.prompt_cache_miss_tokens, 220)
        self.assertAlmostEqual(result.cache_hit_rate, 0.45)


if __name__ == "__main__":
    unittest.main()
