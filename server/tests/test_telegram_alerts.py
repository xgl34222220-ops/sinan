from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.db import database
from app import push_alerts, telegram_alerts


class TelegramAlertTests(unittest.TestCase):
    def setUp(self) -> None:
        push_alerts.initialize()
        with database.connection() as db:
            db.execute("DELETE FROM push_deliveries")
            db.execute("DELETE FROM push_alert_reads")
            db.execute("DELETE FROM push_alerts")
            db.execute("DELETE FROM push_devices")

    @staticmethod
    def watch(source: str = "ai") -> dict:
        source_name = "天机云端 AI" if source == "ai" else "天机云端本地"
        model = "deepseek<pro>" if source == "ai" else "local-ensemble"
        return {
            "threshold": 3,
            "lotteries": [
                {
                    "key": "xyft",
                    "name": "幸运飞艇",
                    "predictions": [
                        {
                            "source": source,
                            "source_name": source_name,
                            "model": model,
                            "warning": True,
                            "current_miss_streak": 3,
                            "recent_three": [
                                {"target_period": "103"},
                                {"target_period": "102"},
                                {"target_period": "101"},
                            ],
                        }
                    ],
                }
            ],
        }

    def test_chat_ids_are_trimmed_and_deduplicated(self) -> None:
        self.assertEqual(
            ("123", "-456", "@channel"),
            telegram_alerts.parse_chat_ids("123, -456\n123; @channel"),
        )

    def test_message_escapes_html_and_contains_periods(self) -> None:
        alert_id = push_alerts.materialize_warning_alerts(self.watch())[0]
        with database.connection() as db:
            alert = db.execute(
                "SELECT * FROM push_alerts WHERE id=?",
                (alert_id,),
            ).fetchone()
        message = telegram_alerts.format_alert_message(alert)
        self.assertIn("deepseek&lt;pro&gt;", message)
        self.assertIn("103、102、101", message)
        self.assertIn("连续未中：</b>3 期", message)

    def test_delivery_works_without_fcm_and_is_idempotent(self) -> None:
        push_alerts.materialize_warning_alerts(self.watch())
        fake_settings = SimpleNamespace(
            fcm_enabled=False,
            telegram_enabled=True,
            telegram_bot_token="123:test-token",
            telegram_chat_ids=("987654321",),
        )
        with patch.object(push_alerts, "settings", fake_settings), patch.object(
            telegram_alerts,
            "send_alert",
            return_value=(True, 200, '{"ok":true}'),
        ) as sender:
            first = push_alerts.deliver_pending_alerts()
            second = push_alerts.deliver_pending_alerts()

        self.assertEqual(1, first["telegram_sent"])
        self.assertEqual(0, first["fcm_sent"])
        self.assertEqual(0, second["telegram_sent"])
        self.assertEqual(1, sender.call_count)

    def test_native_prediction_message_is_suppressed_without_http_request(self) -> None:
        message = (
            "🔮 <b>追踪中的新一期预测</b>\n\n"
            "<b>来源：</b>天机云端本地\n"
            "<b>模型：</b><code>local-ensemble</code>"
        )
        with patch.object(telegram_alerts.requests, "post") as sender:
            result = telegram_alerts.send_html_message(
                bot_token="123:test-token",
                chat_id="987654321",
                text=message,
            )

        self.assertEqual((True, 204, "Telegram 已忽略天机云端本地来源"), result)
        sender.assert_not_called()

    def test_native_warning_is_suppressed_without_http_request(self) -> None:
        alert_id = push_alerts.materialize_warning_alerts(self.watch("native"))[0]
        with database.connection() as db:
            alert = db.execute(
                "SELECT * FROM push_alerts WHERE id=?",
                (alert_id,),
            ).fetchone()

        with patch.object(telegram_alerts.requests, "post") as sender:
            result = telegram_alerts.send_alert(
                bot_token="123:test-token",
                chat_id="987654321",
                alert=alert,
            )

        self.assertEqual((True, 204, "Telegram 已忽略天机云端本地来源"), result)
        sender.assert_not_called()


if __name__ == "__main__":
    unittest.main()
