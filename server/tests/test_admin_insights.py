from __future__ import annotations

import json
import time
import unittest

from app.admin_insights import operations_overview, records_insights, records_page
from app.console_v3 import enhance_console_html
from app.db import database


class AdminInsightsTests(unittest.TestCase):
    def setUp(self) -> None:
        with database.connection() as db:
            db.execute("DELETE FROM forecast_jobs")
            db.execute("DELETE FROM forecasts")
            db.execute("DELETE FROM draws")
            db.execute("DELETE FROM service_state")
        now = int(time.time() * 1000)
        rows = [
            ("xyft", "1001", "1000", 0, [1, 2, 3, 4, 5, 6], "ai", "deepseek-v4-pro", 1, now - 4_000),
            ("xyft", "1002", "1001", 1, [2, 3, 4, 5, 6, 7], "ai", "deepseek-v4-pro", 0, now - 3_000),
            ("azxy10", "2001", "2000", 2, [3, 4, 5, 6, 7, 8], "native", "tianji-native-cloud-v1", 1, now - 2_000),
            ("azxy10", "2002", "2001", 3, [4, 5, 6, 7, 8, 9], "native", "tianji-native-cloud-v1", None, now - 1_000),
        ]
        with database.connection() as db:
            for lottery, target, trained, position, top6, source, model, hit, created in rows:
                db.execute(
                    """
                    INSERT INTO forecasts(
                        lottery,target_period,trained_through_period,position_index,
                        top6_json,top7_json,probabilities_json,source,model,analysis,
                        risk_note,created_at,actual_number,top6_hit,top7_hit,settled_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        lottery,
                        target,
                        trained,
                        position,
                        json.dumps(top6),
                        json.dumps(top6 + [10]),
                        json.dumps([0.1] * 10),
                        source,
                        model,
                        "测试 · 云端耗时 2.5s" if source == "ai" else "本机统计",
                        "仅用于测试",
                        created,
                        1 if hit is not None else None,
                        hit,
                        hit,
                        created + 100 if hit is not None else None,
                    ),
                )
            db.execute(
                "INSERT INTO forecast_jobs(lottery,target_period,source,model,status,message,attempts,claimed_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                ("xyft", "1002", "ai", "deepseek-v4-pro", "completed", "完成", 1, now - 3_100, now - 3_000),
            )

    def test_records_are_paginated_and_filterable(self) -> None:
        first = records_page(limit=2, offset=0)
        self.assertEqual(4, first["total"])
        self.assertEqual(2, len(first["items"]))
        self.assertTrue(first["has_more"])
        ai_only = records_page(source="ai", status="hit")
        self.assertEqual(1, ai_only["total"])
        self.assertEqual("云端 AI", ai_only["items"][0]["source_name"])

    def test_full_history_insights_keep_sources_separate(self) -> None:
        value = records_insights()
        self.assertEqual(4, value["overall"]["count"])
        self.assertEqual(2, value["sources"]["ai"]["count"])
        self.assertEqual(2, value["sources"]["native"]["count"])
        self.assertEqual(0.5, value["sources"]["ai"]["hit_rate"])
        ai_model = next(item for item in value["models"] if item["source"] == "ai")
        self.assertEqual(2.5, ai_model["average_latency_seconds"])
        self.assertEqual(10, len(value["overall"]["positions"]))

    def test_operations_overview_exposes_integrity_and_storage(self) -> None:
        value = operations_overview()
        self.assertIn("auto_update", value)
        self.assertIn("backup", value)
        self.assertIn("storage", value)
        self.assertEqual("ok", value["integrity"]["sqlite"].lower())
        self.assertIsInstance(value["timeline"], list)

    def test_console_enhancer_adds_v3_workspaces(self) -> None:
        html = enhance_console_html(
            "<html><head></head><body><section id='panel-records'></section></body></html>"
        )
        self.assertIn("Cloud Console V3", html)
        self.assertIn("/admin/api/records", html)
        self.assertIn("/admin/api/operations", html)
        self.assertIn("分段真实成绩", html)


if __name__ == "__main__":
    unittest.main()
