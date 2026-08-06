from __future__ import annotations

import os
import tempfile
import unittest

from app.db import Database
from app.migrations import run_migrations
from app.push_runtime_v2 import _plain_text


class PushProtocolV2Test(unittest.TestCase):
    def test_html_message_is_compacted_for_cross_channel_delivery(self) -> None:
        self.assertEqual(
            _plain_text("<b>新一期预测</b>\n\n目标期：<code>123</code>"),
            "新一期预测 · 目标期：123",
        )

    def test_migration_is_idempotent_and_adds_cursor_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Database(os.path.join(directory, "tianji.db"))
            self.assertEqual(run_migrations(target), [1, 2])
            self.assertEqual(run_migrations(target), [])
            with target.connection() as db:
                device_columns = {
                    str(row["name"])
                    for row in db.execute("PRAGMA table_info(push_devices)").fetchall()
                }
                alert_columns = {
                    str(row["name"])
                    for row in db.execute("PRAGMA table_info(push_alerts)").fetchall()
                }
            self.assertIn("read_through_alert_id", device_columns)
            self.assertIn("protocol_version", device_columns)
            self.assertIn("event_type", alert_columns)
            self.assertIn("expires_at", alert_columns)


if __name__ == "__main__":
    unittest.main()
