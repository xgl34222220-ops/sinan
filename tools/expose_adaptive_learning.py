from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = root / "server/app/main.py"
text = main.read_text(encoding="utf-8")
old = '''        "forecasts": [record.model_dump() for record in records],
        "ai_job": database.get_forecast_job(key, "ai"),
    }
'''
new = '''        "forecasts": [record.model_dump() for record in records],
        "ai_job": database.get_forecast_job(key, "ai"),
        "learning": {
            "native": database.strategy_learning_summary(key, "native"),
            "ai": database.strategy_learning_summary(key, "ai"),
        },
    }
'''
if text.count(old) != 1:
    raise SystemExit(f"main.py match count={text.count(old)}")
main.write_text(text.replace(old, new), encoding="utf-8")

test = root / "server/tests/test_adaptive_learning_public.py"
test.write_text('''from __future__ import annotations

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
''', encoding="utf-8")
print("adaptive learning observability applied")
