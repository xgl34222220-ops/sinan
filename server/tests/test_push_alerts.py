from __future__ import annotations

import importlib
import os
import tempfile
import unittest


class PushAlertTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        os.environ["TIANJI_DATABASE"] = os.path.join(self.temp.name, "tianji.db")
        os.environ.pop("TIANJI_FCM_PROJECT_ID", None)
        os.environ.pop("TIANJI_FCM_SERVICE_ACCOUNT_B64", None)
        from app import config, db, push_alerts

        importlib.reload(config)
        importlib.reload(db)
        importlib.reload(push_alerts)
        self.config = config
        self.db = db
        self.push = push_alerts
        self.push.initialize()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_device_registration_hashes_secret_and_keeps_preferences(self) -> None:
        secret = "s" * 32
        status = self.push.register_device(
            installation_id="installation-123",
            secret=secret,
            fcm_token="token-1",
            app_version="5.9.9",
            device_name="Test Device",
            preferences={
                "enabled": True,
                "xyft_enabled": False,
                "azxy10_enabled": True,
                "ai_enabled": True,
                "native_enabled": False,
                "escalation_enabled": True,
            },
        )
        self.assertTrue(status["registered"])
        self.assertTrue(status["fcm_token_present"])
        self.assertFalse(status["push_configured"])
        self.assertFalse(status["preferences"]["xyft_enabled"])
        self.assertFalse(status["preferences"]["native_enabled"])
        with self.db.database.connection() as connection:
            row = connection.execute(
                "SELECT secret_hash FROM push_devices WHERE installation_id=?",
                ("installation-123",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertNotEqual(str(row["secret_hash"]), secret)
        self.assertEqual(len(str(row["secret_hash"])), 64)

    def test_device_registration_rejects_wrong_existing_secret(self) -> None:
        self.push.register_device(
            installation_id="installation-456",
            secret="a" * 32,
        )
        with self.assertRaises(PermissionError):
            self.push.register_device(
                installation_id="installation-456",
                secret="b" * 32,
            )

    def test_alert_is_deduplicated_and_preferences_are_respected(self) -> None:
        secret = "c" * 32
        installation_id = "installation-789"
        self.push.register_device(
            installation_id=installation_id,
            secret=secret,
            preferences={"xyft_enabled": False},
        )
        watch = {
            "threshold": 3,
            "lotteries": [
                {
                    "key": "xyft",
                    "name": "幸运飞艇",
                    "predictions": [
                        {
                            "warning": True,
                            "source": "ai",
                            "source_name": "天机云端 AI",
                            "model": "deepseek-test",
                            "current_miss_streak": 3,
                            "recent_three": [
                                {"target_period": "20260805003"},
                                {"target_period": "20260805002"},
                                {"target_period": "20260805001"},
                            ],
                        }
                    ],
                }
            ],
        }
        first = self.push.materialize_warning_alerts(watch)
        second = self.push.materialize_warning_alerts(watch)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        alerts = self.push.list_alerts(installation_id, secret)["items"]
        self.assertEqual(len(alerts), 1)
        with self.db.database.connection() as connection:
            device = connection.execute(
                "SELECT * FROM push_devices WHERE installation_id=?",
                (installation_id,),
            ).fetchone()
            alert = connection.execute("SELECT * FROM push_alerts").fetchone()
        self.assertFalse(self.push._device_accepts(device, alert))

    def test_mark_read_and_mark_all_read(self) -> None:
        secret = "d" * 32
        installation_id = "installation-read"
        self.push.register_device(installation_id=installation_id, secret=secret)
        watch = {
            "threshold": 3,
            "lotteries": [
                {
                    "key": "azxy10",
                    "name": "澳洲幸运10",
                    "predictions": [
                        {
                            "warning": True,
                            "source": "native",
                            "source_name": "天机云端本地",
                            "model": "native-v1",
                            "current_miss_streak": 4,
                            "recent_three": [
                                {"target_period": "1004"},
                                {"target_period": "1003"},
                                {"target_period": "1002"},
                            ],
                        }
                    ],
                }
            ],
        }
        [alert_id] = self.push.materialize_warning_alerts(watch)
        self.push.mark_alert_read(installation_id, secret, alert_id)
        items = self.push.list_alerts(installation_id, secret)["items"]
        self.assertTrue(items[0]["is_read"])
        result = self.push.mark_all_read(installation_id, secret)
        self.assertEqual(result["count"], 1)


if __name__ == "__main__":
    unittest.main()
