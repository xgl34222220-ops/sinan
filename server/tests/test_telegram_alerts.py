from __future__ import annotations

from types import SimpleNamespace
import time
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
            db.execute(
                "DELETE FROM forecasts WHERE lottery='xyft' AND target_period='103' "
                "AND source='ai' AND model='deepseek<pro>'"
            )
            db.execute("DELETE FROM draws WHERE lottery='xyft' AND period='103'")

    @staticmethod
    def watch(source: str = "ai", streak: int = 3) -> dict:
        source_name = "天机云端 AI" if source == "ai" else "天机云端本地"
        model = "deepseek<pro>" if source == "ai" else "local-ensemble"
        latest = 100 + streak
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
                            "current_miss_streak": streak,
                            "recent_three": [
                                {"target_period": str(latest)},
                                {"target_period": str(latest - 1)},
                                {"target_period": str(latest - 2)},
                            ],
                        }
                    ],
                }
            ],
        }

    @staticmethod
    def seed_fresh_settlement() -> None:
        now = int(time.time() * 1000)
        with database.connection() as db:
            db.execute(
                """
                INSERT INTO draws(
                    lottery,period,numbers_json,draw_time,source,created_at
                ) VALUES('xyft','103','[1,2,3,4,5,6,7,8,9,10]',?,'test',?)
                """,
                (str(now // 1000), now),
            )
            db.execute(
                """
                INSERT INTO forecasts(
                    lottery,target_period,trained_through_period,position_index,
                    top6_json,top7_json,probabilities_json,source,model,analysis,
                    risk_note,created_at,actual_number,top6_hit,top7_hit,settled_at
                ) VALUES(
                    'xyft','103','102',0,'[2,3,4,5,6,7]','[2,3,4,5,6,7,8]',
                    '[0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1]',
                    'ai','deepseek<pro>','','',?,1,0,0,?
                )
                """,
                (now, now),
            )

    def test_chat_ids_are_trimmed_and_deduplicated(self) -> None:
        self.assertEqual(
            ("123", "-456", "@channel"),
            telegram_alerts.parse_chat_ids("123, -456\n123; @channel"),
        )

    def test_two_miss_message_is_a_prealert(self) -> None:
        alert_id = push_alerts.materialize_warning_alerts(self.watch(streak=2))[0]
        with database.connection() as db:
            alert = db.execute(
                "SELECT * FROM push_alerts WHERE id=?",
                (alert_id,),
            ).fetchone()
        message = telegram_alerts.format_alert_message(alert)
        self.assertIn("⚠️", message)
        self.assertIn("连续两期不中 · 提前预警", message)
        self.assertIn("每期云端 AI 预测仍会正常推送", message)

    def test_three_miss_message_is_a_strong_alert(self) -> None:
        alert_id = push_alerts.materialize_warning_alerts(self.watch())[0]
        with database.connection() as db:
            alert = db.execute(
                "SELECT * FROM push_alerts WHERE id=?",
                (alert_id,),
            ).fetchone()
        message = telegram_alerts.format_alert_message(alert)
        self.assertIn("🚨🚨", message)
        self.assertIn("连续三期不中 · 加强提醒", message)
        self.assertIn("deepseek&lt;pro&gt;", message)
        self.assertIn("103、102、101", message)
        self.assertIn("连续未中：</b><b>3 期</b>", message)
        self.assertIn("重点关注下一期预测", message)

    def test_later_miss_message_is_an_escalation_alert(self) -> None:
        alert_id = push_alerts.materialize_warning_alerts(self.watch(streak=4))[0]
        with database.connection() as db:
            alert = db.execute(
                "SELECT * FROM push_alerts WHERE id=?",
                (alert_id,),
            ).fetchone()
        message = telegram_alerts.format_alert_message(alert)
        self.assertIn("连续 4 期不中 · 升级提醒", message)
        self.assertIn("升级提醒状态", message)

    def test_delivery_works_without_fcm_and_is_idempotent(self) -> None:
        self.seed_fresh_settlement()
        push_alerts.materialize_warning_alerts(self.watch())
        fake_settings = SimpleNamespace(
            fcm_enabled=False,
            telegram_enabled=True,
            telegram_bot_token="123:test-token",
            telegram_chat_ids=("987654321",),
            push_retry_seconds=300,
            push_delivery_workers=2,
        )
        with patch.object(push_alerts, "settings", fake_settings), patch.object(
            telegram_alerts,
            "send_alert",
            return_value=(True, 200, '{"ok":true}'),
        ) as sender:
            # Public deliver_pending_alerts() is intentionally non-blocking now. Exercise the
            # canonical batch itself here so transport idempotency remains deterministic.
            first = push_alerts._run_delivery_batch()
            second = push_alerts._run_delivery_batch()

        self.assertEqual(1, first["telegram_sent"])
        self.assertEqual(0, first["fcm_sent"])
        self.assertEqual(0, second["telegram_sent"])
        self.assertEqual(1, sender.call_count)

    def test_native_prediction_message_is_suppressed_without_http_request(self) -> None:
        message = (
            "🔮 <b>新一期云端预测</b>\n\n"
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
