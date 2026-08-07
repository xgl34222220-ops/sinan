from __future__ import annotations

from types import SimpleNamespace
import json
import time
import unittest
from unittest.mock import patch

from app import telegram_alerts, telegram_events
from app.db import database
from app.models import DrawModel


class TelegramEventTests(unittest.TestCase):
    def setUp(self) -> None:
        telegram_events.initialize()
        now = int(time.time() * 1000)
        with database.connection() as db:
            db.execute("DELETE FROM telegram_event_deliveries")
            db.execute("DELETE FROM telegram_events")
            db.execute("DELETE FROM telegram_event_state")
            db.execute("DELETE FROM forecast_jobs")
            db.execute("DELETE FROM forecasts")
            db.execute("DELETE FROM draws")
            db.executemany(
                """
                INSERT INTO telegram_event_state(state_key,state_value,updated_at)
                VALUES(?,?,?)
                """,
                [
                    ("telegram_events_baseline_ms", "0", now),
                    ("telegram_prediction_always_from_ms_v1", "0", now),
                ],
            )

    def save_forecast(
        self,
        *,
        target: str = "100",
        model: str = "deepseek<pro>",
        source: str = "ai",
    ) -> int:
        forecast_id = database.save_forecast(
            lottery="xyft",
            target_period=target,
            trained_through_period=str(int(target) - 1),
            position=0,
            top6=[1, 2, 3, 4, 5, 6],
            top7=[1, 2, 3, 4, 5, 6, 7],
            probabilities=[0.1] * 10,
            source=source,
            model=model,
            analysis="测试",
            risk_note="测试",
        )
        self.assertIsNotNone(forecast_id)
        return int(forecast_id)

    def settle(self, target: str, actual: int) -> None:
        database.save_draws(
            [
                DrawModel(
                    lottery="xyft",
                    period=target,
                    numbers=[actual, 10, 9, 8, 7, 6, 5, 4, 2, 1],
                )
            ]
        )
        self.assertGreaterEqual(database.settle_forecasts("xyft"), 1)

    def create_three_misses(self) -> None:
        for target in ("100", "101", "102"):
            self.save_forecast(target=target)
            self.settle(target, 4)

    def fake_settings(self) -> SimpleNamespace:
        return SimpleNamespace(
            telegram_enabled=True,
            telegram_bot_token="123:test",
            telegram_chat_ids=("987654321",),
        )

    def test_prediction_message_is_sent_normally_without_misses(self) -> None:
        forecast_id = self.save_forecast()
        with database.connection() as db:
            row = db.execute(
                "SELECT * FROM forecasts WHERE id=?",
                (forecast_id,),
            ).fetchone()
        message = telegram_events.format_prediction_message(row, 0)
        self.assertIn("新一期云端 AI 预测", message)
        self.assertIn("deepseek&lt;pro&gt;", message)
        self.assertIn("02、03、05、07、08、10", message)
        self.assertIn("连续未中计数为 0", message)
        self.assertIn("每期推送", message)

    def test_prediction_message_shows_strong_attention_after_three_misses(self) -> None:
        forecast_id = self.save_forecast()
        with database.connection() as db:
            row = db.execute(
                "SELECT * FROM forecasts WHERE id=?",
                (forecast_id,),
            ).fetchone()
        message = telegram_events.format_prediction_message(row, 3)
        self.assertIn("🚨 加强关注", message)
        self.assertIn("连续 3 期未中", message)
        self.assertIn("加强关注阶段", message)

    def test_every_unsettled_ai_prediction_is_materialized(self) -> None:
        self.save_forecast(target="100")
        self.assertEqual(1, telegram_events.materialize_events("xyft"))

        with database.connection() as db:
            row = db.execute(
                "SELECT event_type,target_period,source FROM telegram_events"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual("prediction", str(row["event_type"]))
        self.assertEqual("100", str(row["target_period"]))
        self.assertEqual("ai", str(row["source"]))

    def test_native_prediction_is_not_materialized(self) -> None:
        self.save_forecast(
            target="100",
            source="native",
            model="tianji-native-cloud-v1",
        )
        self.assertEqual(0, telegram_events.materialize_events("xyft"))
        with database.connection() as db:
            count = int(
                db.execute("SELECT COUNT(*) FROM telegram_events").fetchone()[0]
            )
        self.assertEqual(0, count)

    def test_predictions_continue_after_an_ordinary_hit(self) -> None:
        self.save_forecast(target="100")
        self.assertEqual(1, telegram_events.materialize_events("xyft"))
        self.settle("100", 3)

        self.save_forecast(target="101")
        self.assertEqual(1, telegram_events.materialize_events("xyft"))

        with database.connection() as db:
            rows = db.execute(
                """
                SELECT event_type,target_period
                FROM telegram_events
                ORDER BY target_period,event_type
                """
            ).fetchall()
        self.assertEqual(
            [("prediction", "100"), ("prediction", "101")],
            [(str(row["event_type"]), str(row["target_period"])) for row in rows],
        )

    def test_recovery_win_is_sent_only_after_three_misses(self) -> None:
        self.create_three_misses()
        self.save_forecast(target="103")
        self.assertEqual(1, telegram_events.materialize_events("xyft"))

        self.settle("103", 3)
        self.assertEqual(1, telegram_events.materialize_events("xyft"))

        with database.connection() as db:
            rows = db.execute(
                """
                SELECT event_type,target_period,message_html
                FROM telegram_events
                ORDER BY event_type,target_period
                """
            ).fetchall()
        self.assertEqual(
            [("prediction", "103"), ("win", "103")],
            [(str(row["event_type"]), str(row["target_period"])) for row in rows],
        )
        self.assertIn("连续不中后恢复命中", str(rows[1]["message_html"]))
        self.assertIn("下一期云端 AI 预测仍会正常推送", str(rows[1]["message_html"]))

    def test_ordinary_win_does_not_create_win_notification(self) -> None:
        self.save_forecast(target="100")
        self.settle("100", 3)
        self.assertEqual(0, telegram_events.materialize_events("xyft"))
        with database.connection() as db:
            win_count = int(
                db.execute(
                    "SELECT COUNT(*) FROM telegram_events WHERE event_type='win'"
                ).fetchone()[0]
            )
        self.assertEqual(0, win_count)

    def test_delivery_is_idempotent(self) -> None:
        self.save_forecast(target="100")
        telegram_events.materialize_events("xyft")
        with patch.object(
            telegram_events,
            "settings",
            self.fake_settings(),
        ), patch.object(
            telegram_alerts,
            "send_html_message",
            return_value=(True, 200, json.dumps({"ok": True})),
        ) as sender:
            first = telegram_events.deliver_pending_events()
            second = telegram_events.deliver_pending_events()

        self.assertEqual(1, first["sent"])
        self.assertEqual(0, second["sent"])
        self.assertEqual(1, sender.call_count)

    def test_settled_prediction_is_not_sent_late(self) -> None:
        self.save_forecast(target="100")
        telegram_events.materialize_events("xyft")
        self.settle("100", 3)

        with patch.object(
            telegram_events,
            "settings",
            self.fake_settings(),
        ), patch.object(
            telegram_alerts,
            "send_html_message",
            return_value=(True, 200, json.dumps({"ok": True})),
        ) as sender:
            result = telegram_events.deliver_pending_events()

        self.assertEqual(0, result["sent"])
        self.assertEqual(1, result["skipped"])
        self.assertEqual(0, sender.call_count)

    def test_stale_prediction_is_suppressed_instead_of_sent_late(self) -> None:
        self.save_forecast(target="100")
        telegram_events.materialize_events("xyft")
        stale_at = int(time.time() * 1000) - 9 * 60_000
        with database.connection() as db:
            db.execute(
                "UPDATE telegram_events SET created_at=? WHERE event_key LIKE 'prediction:%'",
                (stale_at,),
            )

        with patch.object(
            telegram_events,
            "settings",
            self.fake_settings(),
        ), patch.object(
            telegram_alerts,
            "send_html_message",
            return_value=(True, 200, json.dumps({"ok": True})),
        ) as sender:
            result = telegram_events.deliver_pending_events()

        self.assertEqual(0, result["sent"])
        self.assertEqual(1, result["skipped"])
        self.assertEqual(0, sender.call_count)
        with database.connection() as db:
            delivery = db.execute(
                "SELECT status,message FROM telegram_event_deliveries LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(delivery)
        self.assertEqual("suppressed", str(delivery["status"]))
        self.assertIn("超过8分钟", str(delivery["message"]))

    def test_prediction_start_watermark_prevents_historical_backfill(self) -> None:
        self.save_forecast(target="100")
        future = int(time.time() * 1000) + 60_000
        with database.connection() as db:
            db.execute(
                """
                UPDATE telegram_event_state
                SET state_value=?,updated_at=?
                WHERE state_key='telegram_prediction_always_from_ms_v1'
                """,
                (str(future), int(time.time() * 1000)),
            )

        self.assertEqual(0, telegram_events.materialize_events("xyft"))


if __name__ == "__main__":
    unittest.main()
