from __future__ import annotations

import inspect
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import ai, ai_ensemble, service
from app.runtime_config import RuntimeAiConfig


class AiOriginalEngineDeadlineTests(unittest.TestCase):
    @staticmethod
    def config() -> RuntimeAiConfig:
        return RuntimeAiConfig(
            enabled=True,
            endpoint="https://api.deepseek.com/chat/completions",
            model="deepseek-v4-pro",
            api_key="secret",
            timeout_seconds=120,
        )

    def test_full_dynamic_v2_transport_and_reviewer_scheduler_are_not_runtime_replaced(self) -> None:
        # Deadline handling must never change the provider request body, thinking mode,
        # token budget, retry behavior or the original prefix-cache reviewer order.
        self.assertEqual("app.ai", ai.analyze.__module__)
        self.assertEqual("analyze", ai.analyze.__name__)
        self.assertEqual("app.ai_ensemble", ai_ensemble._call_json.__module__)
        self.assertEqual("_call_json", ai_ensemble._call_json.__name__)
        self.assertEqual("app.ai_ensemble", ai_ensemble._run_prefix_cached.__module__)
        self.assertEqual("_run_prefix_cached", ai_ensemble._run_prefix_cached.__name__)

    def test_publish_guard_is_exactly_40_seconds(self) -> None:
        self.assertEqual(40_000, service.AI_PUBLISH_GUARD_MS)

    def test_target_is_rejected_inside_40_second_publish_guard(self) -> None:
        now_seconds = 1_800_000_000.0
        now_ms = int(now_seconds * 1000)
        latest = SimpleNamespace(period="21348747")
        spec = SimpleNamespace(key="azxy10")
        with (
            patch("app.service.time.time", return_value=now_seconds),
            patch.object(
                service.lottery_client,
                "fetch_latest",
                return_value=(latest, "21348748", now_ms, now_ms + 39_999),
            ),
            patch.object(service.database, "get_draw", return_value=None),
        ):
            self.assertFalse(service._target_is_open(spec, "21348747", "21348748"))

    def test_target_can_publish_before_40_second_guard(self) -> None:
        now_seconds = 1_800_000_000.0
        now_ms = int(now_seconds * 1000)
        latest = SimpleNamespace(period="21348747")
        spec = SimpleNamespace(key="azxy10")
        with (
            patch("app.service.time.time", return_value=now_seconds),
            patch.object(
                service.lottery_client,
                "fetch_latest",
                return_value=(latest, "21348748", now_ms, now_ms + 40_001),
            ),
            patch.object(service.database, "get_draw", return_value=None),
        ):
            self.assertTrue(service._target_is_open(spec, "21348747", "21348748"))

    def test_ai_is_scheduled_after_settlement_but_before_notifications_and_native(self) -> None:
        source = inspect.getsource(service.run_lottery_cycle)
        settle = source.index('"settle_forecasts"')
        history = source.index('"load_history"')
        schedule = source.index('"schedule_ai_early"')
        push = source.index('"deliver_push"')
        telegram = source.index('"deliver_telegram"')
        native = source.index('"generate_native"')
        self.assertLess(settle, history)
        self.assertLess(history, schedule)
        self.assertLess(schedule, push)
        self.assertLess(schedule, telegram)
        self.assertLess(schedule, native)

    def test_start_lead_is_only_a_resource_guard(self) -> None:
        # Keep enough budget to avoid starting a full-quality multi-review job too late.
        # This threshold affects whether a job starts, never how its numbers are computed.
        self.assertEqual(225_000, service._minimum_ai_lead_ms(self.config()))


if __name__ == "__main__":
    unittest.main()
