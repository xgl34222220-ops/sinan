from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from app.db import Database
from app.models import DrawModel
from app import main


class AdaptiveLearningPublicTests(unittest.TestCase):
    def test_lottery_overview_exposes_exact_learning_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/public-learning.db")
            with db.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO strategy_learning(
                        lottery, source, strategy, weight, samples,
                        ema_log_loss, ema_brier, top6_hits, top6_misses, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("xyft", "native", "trend", 0.123456789, 7, 2.1, 0.82, 5, 2, 123456),
                )
            with patch.object(main, "database", db):
                value = main._lottery_overview("xyft")
            learning = value["learning"]["native"]
            self.assertEqual(len(learning), 1)
            self.assertEqual(learning[0]["strategy"], "trend")
            self.assertEqual(learning[0]["weight"], 0.123456789)
            self.assertEqual(learning[0]["samples"], 7)
            self.assertEqual(learning[0]["top6_hits"], 5)


if __name__ == "__main__":
    unittest.main()
