from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app import deployment_status as deployment_module
from app import push_delivery_v3, telegram_alerts


class DeploymentStatusTests(unittest.TestCase):
    def test_updated_status_reports_current_commit(self) -> None:
        with TemporaryDirectory() as directory:
            Path(directory, "auto-update-status.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "message": "部署成功",
                        "from_commit": "a" * 40,
                        "to_commit": "b" * 40,
                        "updated_at_epoch_ms": 123456,
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(
                deployment_module,
                "settings",
                SimpleNamespace(data_dir=directory),
            ):
                value = deployment_module.deployment_status("1.6.0")

        self.assertEqual(value["current_commit"], "b" * 12)
        self.assertEqual(value["target_commit"], "b" * 12)
        self.assertTrue(value["is_current"])
        self.assertFalse(value["requires_attention"])

    def test_rolled_back_status_keeps_previous_commit(self) -> None:
        with TemporaryDirectory() as directory:
            Path(directory, "auto-update-status.json").write_text(
                json.dumps(
                    {
                        "status": "rolled_back",
                        "from_commit": "1" * 40,
                        "to_commit": "2" * 40,
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(
                deployment_module,
                "settings",
                SimpleNamespace(data_dir=directory),
            ):
                value = deployment_module.deployment_status("1.6.0")

        self.assertEqual(value["current_commit"], "1" * 12)
        self.assertEqual(value["target_commit"], "2" * 12)
        self.assertFalse(value["is_current"])
        self.assertTrue(value["requires_attention"])


class PushDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alert = {
            "id": 91,
            "event_key": "event-91",
            "lottery": "xyft",
            "lottery_name": "幸运飞艇",
            "source": "ai",
            "source_name": "天机云端 AI",
            "model": "deepseek-chat",
            "streak": 2,
            "threshold": 3,
            "latest_target_period": "20260806001",
            "recent_periods_json": json.dumps(["20260806001", "20260806000"]),
            "title": "两期不中预警",
            "body": "云端 AI 已连续两期未命中",
            "data_json": json.dumps({"type": "prediction_miss_alert"}),
            "created_at": 123456789,
        }

    def test_message_data_contains_complete_local_notification_payload(self) -> None:
        value = push_delivery_v3.message_data(self.alert)
        self.assertEqual(value["alert_id"], "91")
        self.assertEqual(value["title"], "两期不中预警")
        self.assertEqual(value["body"], "云端 AI 已连续两期未命中")
        self.assertEqual(value["event_type"], "miss_prealert")
        self.assertEqual(value["schema_version"], "2")
        self.assertEqual(value["recent_periods"], "20260806001,20260806000")

    def test_fcm_message_is_data_only(self) -> None:
        credentials = SimpleNamespace(token="oauth-token")
        module = SimpleNamespace(_credentials=lambda: credentials)
        response = Mock(ok=True, status_code=200, text="ok")
        with patch.object(push_delivery_v3.requests, "post", return_value=response) as post:
            ok, code, _message = push_delivery_v3.send_data_message(
                module,
                "device-token",
                self.alert,
            )

        self.assertTrue(ok)
        self.assertEqual(code, 200)
        payload = post.call_args.kwargs["json"]["message"]
        self.assertIn("data", payload)
        self.assertNotIn("notification", payload)
        self.assertEqual(payload["android"]["priority"], "HIGH")


class TelegramVisualTests(unittest.TestCase):
    def test_alert_message_is_compact_and_contains_key_fields(self) -> None:
        alert = {
            "title": "三期不中加强提醒",
            "lottery_name": "幸运飞艇",
            "source_name": "天机云端 AI",
            "source": "ai",
            "model": "deepseek-chat",
            "streak": 3,
            "threshold": 3,
            "latest_target_period": "20260806001",
            "recent_periods_json": json.dumps(["001", "000", "999"]),
        }
        text = telegram_alerts.format_alert_message(alert)
        self.assertIn("连续三期不中", text)
        self.assertIn("deepseek-chat", text)
        self.assertIn("20260806001", text)
        self.assertNotIn("下一次两期不中先预警", text)

    def test_reply_markup_uses_public_base_url(self) -> None:
        with patch.object(
            telegram_alerts,
            "settings",
            SimpleNamespace(public_base_url="https://example.test"),
        ):
            markup = telegram_alerts._reply_markup()
        self.assertIsNotNone(markup)
        buttons = markup["inline_keyboard"][0]
        self.assertEqual(buttons[0]["url"], "https://example.test")
        self.assertEqual(buttons[1]["url"], "https://example.test/admin")


if __name__ == "__main__":
    unittest.main()
