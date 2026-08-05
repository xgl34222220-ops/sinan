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

    def test_prediction_message_escapes_model_and_contains_top6(self) -> None:
        forecast_id = self.save_forecast()
        with database.connection() as db:
            row = db.execute("SELECT * FROM forecasts WHERE id=?", (forecast_id,)).fetchone()
        message = telegram_events.format_prediction_message(row)
        self.assertIn("deepseek&lt;pro&gt;", message)
        self.assertIn("01、02、03、04、05、06", message)
        self.assertIn("新一期预测", message)

    def test_materializes_prediction_and_top6_win_once(self) -> None:
        self.save_forecast()
        database.save_draws(
            [
                DrawModel(
                    lottery="xyft",
                    period="100",
                    numbers=[3, 10, 9, 8, 7, 6, 5, 4, 2, 1],
                )
            ]
        )
        self.assertEqual(1, database.settle_forecasts("xyft"))
        first = telegram_events.materialize_events("xyft")
        second = telegram_events.materialize_events("xyft")
        with database.connection() as db:
            rows = db.execute(
                "SELECT event_type,message_html FROM telegram_events ORDER BY event_type"
            ).fetchall()
        self.assertEqual(2, first)
        self.assertEqual(0, second)
        self.assertEqual(["prediction", "win"], [str(row["event_type"]) for row in rows])
        self.assertIn("实际号码：</b><b>03", str(rows[1]["message_html"]))

    def test_miss_does_not_create_win_event(self) -> None:
        self.save_forecast()
        database.save_draws(
            [
                DrawModel(
                    lottery="xyft",
                    period="100",
                    numbers=[10, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                )
            ]
        )
        database.settle_forecasts("xyft")
        telegram_events.materialize_events("xyft")
        with database.connection() as db:
            types = [
                str(row["event_type"])
                for row in db.execute("SELECT event_type FROM telegram_events").fetchall()
            ]
        self.assertEqual(["prediction"], types)

    def test_delivery_is_idempotent(self) -> None:
        self.save_forecast()
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


if __name__ == "__main__":
    unittest.main()
