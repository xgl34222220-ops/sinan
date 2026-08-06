from __future__ import annotations

import unittest

from app import admin_insights
from app.runtime_patches import (
    _requires_independence_audit,
    _scope_streak,
    _top6_overlap,
)


class RuntimeAccuracyPatchTests(unittest.TestCase):
    @staticmethod
    def record(
        *,
        record_id: int,
        lottery: str,
        source: str,
        model: str,
        period: str,
        hit: bool | None,
        created: int,
        position: int = 0,
    ) -> dict:
        return {
            "id": record_id,
            "lottery": lottery,
            "source": source,
            "model": model,
            "target_period": period,
            "top6_hit": hit,
            "position": position,
            "analysis": "",
            "created_at_epoch_ms": created,
        }

    def test_longest_miss_isolated_by_lottery_source_and_model(self) -> None:
        rows = []
        record_id = 1
        for offset in range(6):
            rows.append(
                self.record(
                    record_id=record_id,
                    lottery="xyft",
                    source="ai",
                    model="deepseek-v4",
                    period=str(106 - offset),
                    hit=False,
                    created=1_000 - offset * 2,
                )
            )
            record_id += 1
            rows.append(
                self.record(
                    record_id=record_id,
                    lottery="azxy10",
                    source="native",
                    model="native-v4",
                    period=str(206 - offset),
                    hit=True,
                    created=999 - offset * 2,
                )
            )
            record_id += 1

        streak = _scope_streak(rows)
        self.assertEqual(streak["longest_miss"], 6)
        self.assertEqual(streak["current"], 6)
        self.assertEqual(streak["current_type"], "miss")
        self.assertEqual(streak["longest_miss_leader"]["lottery"], "xyft")
        self.assertEqual(streak["longest_miss_leader"]["model"], "deepseek-v4")

    def test_duplicate_target_period_does_not_inflate_streak(self) -> None:
        rows = [
            self.record(
                record_id=4,
                lottery="xyft",
                source="ai",
                model="model-a",
                period="103",
                hit=False,
                created=103,
            ),
            self.record(
                record_id=3,
                lottery="xyft",
                source="ai",
                model="model-a",
                period="102",
                hit=False,
                created=102,
            ),
            self.record(
                record_id=2,
                lottery="xyft",
                source="ai",
                model="model-a",
                period="102",
                hit=False,
                created=101,
            ),
            self.record(
                record_id=1,
                lottery="xyft",
                source="ai",
                model="model-a",
                period="101",
                hit=True,
                created=100,
            ),
        ]

        streak = _scope_streak(rows)
        self.assertEqual(streak["current"], 2)
        self.assertEqual(streak["longest_miss"], 2)

    def test_group_summary_exposes_independent_window_streaks(self) -> None:
        rows = [
            self.record(
                record_id=index,
                lottery="xyft",
                source="ai",
                model="model-a",
                period=str(200 - index),
                hit=False if index <= 7 else True,
                created=500 - index,
            )
            for index in range(1, 12)
        ]
        summary = admin_insights._group_summary(rows)
        self.assertEqual(summary["streak"]["longest_miss"], 7)
        self.assertIn("streak", summary["windows"]["20"])
        self.assertEqual(summary["windows"]["20"]["streak"]["longest_miss"], 7)

    def test_ai_overlap_guard_triggers_at_five_of_six(self) -> None:
        self.assertEqual(_top6_overlap([1, 2, 3, 4, 5, 6], [2, 3, 4, 5, 6, 7]), 5)
        self.assertTrue(
            _requires_independence_audit(
                [1, 2, 3, 4, 5, 6],
                [2, 3, 4, 5, 6, 7],
            )
        )
        self.assertFalse(
            _requires_independence_audit(
                [1, 2, 3, 4, 5, 6],
                [3, 4, 5, 6, 7, 8],
            )
        )


if __name__ == "__main__":
    unittest.main()
