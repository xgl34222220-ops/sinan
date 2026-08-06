from __future__ import annotations

import unittest

from app.push_freshness_guard import _warning_candidate_is_fresh


class PushFreshnessGuardTest(unittest.TestCase):
    NOW = 1_800_000_000_000

    def candidate(self, **overrides):
        value = {
            "target_period": "20260806001",
            "latest_period": "20260806001",
            "settled_at": self.NOW - 30_000,
            "draw_time": str((self.NOW - 60_000) // 1000),
            "created_at": self.NOW - 20_000,
            "now_ms": self.NOW,
        }
        value.update(overrides)
        return _warning_candidate_is_fresh(**value)

    def test_accepts_only_a_just_settled_current_draw(self) -> None:
        self.assertTrue(self.candidate())

    def test_rejects_previous_session_draw_even_if_backfill_settled_now(self) -> None:
        self.assertFalse(
            self.candidate(draw_time=str((self.NOW - 12 * 60 * 60 * 1000) // 1000))
        )

    def test_rejects_stale_delivery_backlog(self) -> None:
        self.assertFalse(
            self.candidate(created_at=self.NOW - 31 * 60 * 1000)
        )

    def test_rejects_non_latest_period(self) -> None:
        self.assertFalse(self.candidate(latest_period="20260806002"))

    def test_rejects_missing_or_old_settlement(self) -> None:
        self.assertFalse(self.candidate(settled_at=None))
        self.assertFalse(
            self.candidate(settled_at=self.NOW - 21 * 60 * 1000)
        )

    def test_rejects_unknown_draw_time_fail_closed(self) -> None:
        self.assertFalse(self.candidate(draw_time=""))


if __name__ == "__main__":
    unittest.main()
