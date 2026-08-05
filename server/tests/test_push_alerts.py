from __future__ import annotations

import unittest

from app.db import database
from app.push_alerts import (
    DevicePreferences,
    device_status,
    initialize,
    list_alerts,
    mark_alert_read,
    materialize_warning_alerts,
    register_device,
    update_preferences,
)


class PushAlertsTests(unittest.TestCase):
    def setUp(self) -> None:
        initialize()
        with database.connection() as db:
            db.execute("DELETE FROM push_deliveries")
            db.execute("DELETE FROM push_alert_reads")
            db.execute("DELETE FROM push_alerts")
            db.execute("DELETE FROM push_devices")

    @staticmethod
    def watch(streak: int = 3, latest: str = "103") -> dict:
        return {
            "threshold": 3,
            "lotteries": [
                {
                    "key": "xyft",
                    "name": "幸运飞艇",
                    "predictions": [
                        {
                            "source": "ai",
                            "source_name": "天机云端 AI",
                            "model": "deepseek-v4",
                            "warning": True,
                            "current_miss_streak": streak,
                            "recent_three": [
                                {"target_period": latest},
                                {"target_period": str(int(latest) - 1)},
                                {"target_period": str(int(latest) - 2)},
                            ],
                        }
                    ],
                }
            ],
        }

    def register(self) -> tuple[str, str]:
        installation_id = "test-installation-123456"
        secret = "a" * 64
        register_device(
            installation_id=installation_id,
            secret=secret,
            app_version="5.9.9-test",
            preferences=DevicePreferences().as_dict(),
        )
        return installation_id, secret

    def test_device_secret_and_preferences(self) -> None:
        installation_id, secret = self.register()
        status = device_status(installation_id, secret)
        self.assertTrue(status["registered"])
        self.assertTrue(status["preferences"]["xyft_enabled"])

        updated = update_preferences(
            installation_id,
            secret,
            {
                "enabled": True,
                "xyft_enabled": False,
                "azxy10_enabled": True,
                "ai_enabled": True,
                "native_enabled": False,
                "escalation_enabled": False,
            },
        )
        self.assertFalse(updated["preferences"]["xyft_enabled"])
        self.assertFalse(updated["preferences"]["native_enabled"])

        with self.assertRaises(PermissionError):
            device_status(installation_id, "b" * 64)

    def test_warning_is_idempotent_and_escalation_is_separate(self) -> None:
        first = materialize_warning_alerts(self.watch())
        duplicate = materialize_warning_alerts(self.watch())
        escalation = materialize_warning_alerts(self.watch(streak=4, latest="104"))
        self.assertEqual(1, len(first))
        self.assertEqual([], duplicate)
        self.assertEqual(1, len(escalation))
        with database.connection() as db:
            count = int(db.execute("SELECT COUNT(*) FROM push_alerts").fetchone()[0])
        self.assertEqual(2, count)

    def test_alert_read_state_is_per_device(self) -> None:
        installation_id, secret = self.register()
        alert_id = materialize_warning_alerts(self.watch())[0]
        unread = list_alerts(installation_id, secret)["items"]
        self.assertFalse(unread[0]["is_read"])
        mark_alert_read(installation_id, secret, alert_id)
        read = list_alerts(installation_id, secret)["items"]
        self.assertTrue(read[0]["is_read"])


if __name__ == "__main__":
    unittest.main()
