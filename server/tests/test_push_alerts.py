from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
import time

from app.db import database
from app.push_alerts import (
    DevicePreferences,
    _claim_delivery,
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

    def test_two_miss_prealert_strong_alert_and_escalation_are_separate(self) -> None:
        prealert = materialize_warning_alerts(self.watch(streak=2, latest="102"))
        duplicate = materialize_warning_alerts(self.watch(streak=2, latest="102"))
        strong = materialize_warning_alerts(self.watch(streak=3, latest="103"))
        escalation = materialize_warning_alerts(self.watch(streak=4, latest="104"))
        self.assertEqual(1, len(prealert))
        self.assertEqual([], duplicate)
        self.assertEqual(1, len(strong))
        self.assertEqual(1, len(escalation))
        with database.connection() as db:
            rows = db.execute(
                "SELECT streak,threshold,title FROM push_alerts ORDER BY streak"
            ).fetchall()
        self.assertEqual(
            [
                (2, 3, "两期不中预警"),
                (3, 3, "三期不中加强提醒"),
                (4, 3, "连续 4 期不中升级预警"),
            ],
            [
                (int(row["streak"]), int(row["threshold"]), str(row["title"]))
                for row in rows
            ],
        )

    def test_alert_read_state_is_per_device(self) -> None:
        installation_id, secret = self.register()
        alert_id = materialize_warning_alerts(self.watch())[0]
        unread = list_alerts(installation_id, secret)["items"]
        self.assertFalse(unread[0]["is_read"])
        mark_alert_read(installation_id, secret, alert_id)
        read = list_alerts(installation_id, secret)["items"]
        self.assertTrue(read[0]["is_read"])


    def test_delivery_claim_is_atomic_across_parallel_cycles(self) -> None:
        alert_id = materialize_warning_alerts(self.watch(streak=2, latest="202"))[0]
        now = int(time.time() * 1000)

        def claim(_index: int) -> bool:
            return _claim_delivery(
                alert_id=alert_id,
                target_key="telegram:test-chat",
                attempted_at=now,
                retry_before=now - 300_000,
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(claim, range(8)))
        self.assertEqual(1, sum(bool(value) for value in results))


if __name__ == "__main__":
    unittest.main()
