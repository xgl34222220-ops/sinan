from __future__ import annotations

from types import SimpleNamespace
import json
import time
import unittest
from unittest.mock import patch

from app import telegram_events, telegram_alerts
from app.db import database
from app.models import DrawModel


class TelegramEventTests(unittest.TestCase):
    def setUp(self) -> None:
        telegram_events.initialize()
        with database.connection() as db:
            db.execute("DELETE FROM telegram_event_deliveries")
            db.execute("DELETE FROM telegram_events")
            db.execute("DELETE FROM telegram_event_state")
            db.execute("DELETE FROM forecast_jobs")
            db.execute("DELETE FROM forecasts")
            db.execute("DELETE FROM draws")
            db.execute(
                """
                INSERT INTO telegram_event_state(state_key,state_value,updated_at)
                VALUES(?,?,?)
                """,
                ("telegram_events_baseline_ms", "0", int(time.time() * 1000)),
            )

    def save_forecast(self, *, target: str = "100", model: str = "deepseek<pro>") -> int:
        forecast_id = database.save_forecast(
            lottery="xyft",
            target_period=target,
            trained_through_period=str(int(target) - 1),
            position=0,
            top6=[1, 2, 3, 4, 5, 6],
            top7=[1, 2, 3, 4, 5, 6, 7],
            probabilities=[0.1] * 10,
            source="ai",
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
        self.assertEqual(1, database.settle_forecasts("xyft"))

    def activate_tracking(self) -> None:
        self.save_forecast(target="100")
        self.settle("100", 10)
        self.save_forecast(target="101")
        self.settle("101", 10)

    def test_prediction_message_escapes_model_and_contains_top6(self) -> None:
        forecast_id = self.save_forecast()
        with database.connection() as db:
            row = db.execute("SELECT * FROM forecasts WHERE id=?", (forecast_id,)).fetchone()
        message = telegram_events.format_prediction_message(row, 2)
        self.assertIn("deepseek&lt;pro&gt;", message)
        self.assertIn("01、02、03、04、05、06", message)
        self.assertIn("追踪中的新一期预测", message)
        self.assertIn("连续 2 期未中", message)
        self.assertIn("命中后自动停止", message)

    def test_prediction_waits_for_two_misses_and_stops_after_hit(self) -> None:
        self.activate_tracking()
        self.save_forecast(target="102")

        first = telegram_events.materialize_events("xyft")
        self.assertEqual(1, first)

        self.settle("102", 3)
        self.save_forecast(target="103")
        second = telegram_events.materialize_events("xyft")
        self.assertEqual(1, second)

        with database.connection() as db:
            rows = db.execute(
                """
                SELECT event_type,target_period,message_html
                FROM telegram_events
                ORDER BY event_type,target_period
                """
            ).fetchall()
        self.assertEqual(
            [("prediction", "102"), ("win", "102")],
            [(str(row["event_type"]), str(row["target_period"])) for row in rows],
        )
        self.assertIn("追踪预测推送现已停止", str(rows[1]["message_html"]))

    def test_tracking_continues_after_another_miss(self) -> None:
        self.activate_tracking()
        self.save_forecast(target="102")
        self.assertEqual(1, telegram_events.materialize_events("xyft"))

        self.settle("102", 10)
        self.save_forecast(target="103")
        self.assertEqual(1, telegram_events.materialize_events("xyft"))

        with database.connection() as db:
            periods = [
                str(row["target_period"])
                for row in db.execute(
                    """
                    SELECT target_period FROM telegram_events
                    WHERE event_type='prediction'
                    ORDER BY target_period
                    """
                ).fetchall()
            ]
        self.assertEqual(["102", "103"], periods)

    def test_miss_does_not_create_win_event(self) -> None:
        self.activate_tracking()
        self.save_forecast(target="102")
        self.settle("102", 10)
        telegram_events.materialize_events("xyft")
        with database.connection() as db:
            types = [
                str(row["event_type"])
                for row in db.execute("SELECT event_type FROM telegram_events").fetchall()
            ]
        self.assertEqual(["prediction"], types)

    def test_delivery_is_idempotent(self) -> None:
        self.activate_tracking()
        self.save_forecast(target="102")
        telegram_events.materialize_events("xyft")
        fake_settings = SimpleNamespace(
            telegram_enabled=True,
            telegram_bot_token="123:test",
            telegram_chat_ids=("987654321",),
        )
        with patch.object(telegram_events, "settings", fake_settings), patch.object(
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
        self.activate_tracking()
        self.save_forecast(target="102")
        telegram_events.materialize_events("xyft")
        self.settle("102", 3)
        telegram_events.materialize_events("xyft")

        fake_settings = SimpleNamespace(
            telegram_enabled=True,
            telegram_bot_token="123:test",
            telegram_chat_ids=("987654321",),
        )
        sent_messages: list[str] = []

        def fake_send(**kwargs: str) -> tuple[bool, int, str]:
            sent_messages.append(str(kwargs["text"]))
            return True, 200, json.dumps({"ok": True})

        with patch.object(telegram_events, "settings", fake_settings), patch.object(
            telegram_alerts,
            "send_html_message",
            side_effect=fake_send,
        ):
            result = telegram_events.deliver_pending_events()

        self.assertEqual(1, result["sent"])
        self.assertEqual(1, len(sent_messages))
        self.assertIn("Top 6 命中", sent_messages[0])
        self.assertNotIn("追踪中的新一期预测", sent_messages[0])


if __name__ == "__main__":
    unittest.main()
