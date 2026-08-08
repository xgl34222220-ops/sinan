from __future__ import annotations

from types import SimpleNamespace
import threading
import unittest
from unittest.mock import MagicMock, patch

from app import ai_deadline_fast, ai_ensemble, service
from app.runtime_config import RuntimeAiConfig


class AiDeadlineFastTests(unittest.TestCase):
    def config(self) -> RuntimeAiConfig:
        return RuntimeAiConfig(
            enabled=True,
            endpoint="https://api.deepseek.com/chat/completions",
            model="deepseek-v4-pro",
            api_key="secret",
            timeout_seconds=120,
        )

    def test_new_ai_job_requires_225_seconds_of_lead(self) -> None:
        self.assertEqual(
            service._minimum_ai_lead_ms(self.config()),
            ai_deadline_fast.AI_MIN_START_LEAD_MS,
        )
        self.assertEqual(ai_deadline_fast.AI_MIN_START_LEAD_MS, 225_000)

    def test_target_is_rejected_inside_90_second_publish_guard(self) -> None:
        now_seconds = 1_800_000_000.0
        now_ms = int(now_seconds * 1000)
        latest = SimpleNamespace(period="21348747")
        spec = SimpleNamespace(key="azxy10")
        with (
            patch("app.ai_deadline_fast.time.time", return_value=now_seconds),
            patch.object(
                service.lottery_client,
                "fetch_latest",
                return_value=(
                    latest,
                    "21348748",
                    now_ms,
                    now_ms + ai_deadline_fast.AI_PUBLISH_GUARD_MS - 1,
                ),
            ),
            patch.object(service.database, "get_draw", return_value=None),
        ):
            self.assertFalse(
                service._target_is_open(spec, "21348747", "21348748")
            )

    def test_target_can_publish_before_guard(self) -> None:
        now_seconds = 1_800_000_000.0
        now_ms = int(now_seconds * 1000)
        latest = SimpleNamespace(period="21348747")
        spec = SimpleNamespace(key="azxy10")
        with (
            patch("app.ai_deadline_fast.time.time", return_value=now_seconds),
            patch.object(
                service.lottery_client,
                "fetch_latest",
                return_value=(
                    latest,
                    "21348748",
                    now_ms,
                    now_ms + ai_deadline_fast.AI_PUBLISH_GUARD_MS + 30_000,
                ),
            ),
            patch.object(service.database, "get_draw", return_value=None),
        ):
            self.assertTrue(
                service._target_is_open(spec, "21348747", "21348748")
            )

    def test_live_review_phase_starts_all_reviewers_in_parallel(self) -> None:
        barrier = threading.Barrier(3)
        started: list[int] = []
        lock = threading.Lock()

        def task(reviewer: int) -> int:
            with lock:
                started.append(reviewer)
            barrier.wait(timeout=2.0)
            return reviewer

        with ai_deadline_fast._deadline_fast_context():
            results = ai_ensemble._run_prefix_cached(3, task)
        self.assertEqual(set(started), {0, 1, 2})
        self.assertEqual(set(results), {0, 1, 2})

    def test_deepseek_first_live_request_disables_thinking_and_caps_output(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"scores":{"A":1,"B":2,"C":3,"D":4,"E":5,"F":6,"G":7,"H":8,"I":9,"J":10},"analysis":"快速评审"}'
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        }
        client = MagicMock()
        client.post.return_value = response
        client_cm = MagicMock()
        client_cm.__enter__.return_value = client
        client_cm.__exit__.return_value = False

        with (
            patch("app.ai_deadline_fast.httpx.Client", return_value=client_cm),
            ai_deadline_fast._deadline_fast_context(),
        ):
            result = ai_deadline_fast._fast_call_json(
                self.config(),
                system_prompt="test",
                user_payload={"target": "21348748"},
                max_tokens=1400,
                timeout_seconds=50,
            )

        request_body = client.post.call_args.kwargs["json"]
        self.assertEqual(request_body["thinking"], {"type": "disabled"})
        self.assertLessEqual(request_body["max_tokens"], ai_deadline_fast.AI_MAX_FAST_TOKENS)
        self.assertIn("scores", result)


if __name__ == "__main__":
    unittest.main()
