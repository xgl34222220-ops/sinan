from __future__ import annotations

import tempfile
import unittest

from app.adaptive_learning import (
    blend_strategy_probabilities,
    prediction_loss,
    strategy_components,
    update_strategy_weights,
)
from app.db import Database
from app.models import DrawModel


def history(count: int = 160) -> list[DrawModel]:
    rows: list[DrawModel] = []
    base = list(range(1, 11))
    for index in range(count):
        shift = (index * 3 + index // 7) % 10
        numbers = base[shift:] + base[:shift]
        rows.append(
            DrawModel(
                lottery="xyft",
                period=str(100000 + index),
                numbers=numbers,
            )
        )
    return rows


class AdaptiveLearningTests(unittest.TestCase):
    def test_components_are_distinct_normalized_probabilities(self) -> None:
        components = strategy_components(history(), 0)
        self.assertGreaterEqual(len(components), 7)
        for probabilities in components.values():
            self.assertEqual(len(probabilities), 10)
            self.assertAlmostEqual(sum(probabilities), 1.0, places=8)
        unique = {tuple(round(value, 8) for value in item) for item in components.values()}
        self.assertGreater(len(unique), 3)

    def test_good_strategy_gains_weight_and_bad_strategy_loses_weight(self) -> None:
        good = [0.04] * 10
        bad = [0.106] * 10
        good[2] = 0.64
        bad[2] = 0.046
        good_loss = prediction_loss(good, 3)["combined_loss"]
        bad_loss = prediction_loss(bad, 3)["combined_loss"]
        updated = update_strategy_weights(
            {"good": 0.5, "bad": 0.5},
            {"good": float(good_loss), "bad": float(bad_loss)},
        )
        self.assertGreater(updated["good"], 0.5)
        self.assertLess(updated["bad"], 0.5)
        self.assertAlmostEqual(sum(updated.values()), 1.0, places=8)

    def test_settlement_persists_scores_and_updates_next_weights(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(f"{directory}/adaptive.db")
            forecast_id = database.save_forecast(
                lottery="xyft",
                target_period="200001",
                trained_through_period="200000",
                position=0,
                top6=[1, 2, 3, 4, 5, 6],
                top7=[1, 2, 3, 4, 5, 6, 7],
                probabilities=[0.1] * 10,
                source="native",
                model="test-adaptive",
                analysis="测试",
                risk_note="测试",
            )
            assert forecast_id is not None
            good = [0.04] * 10
            bad = [0.106] * 10
            good[2] = 0.64
            bad[2] = 0.046
            database.save_strategy_predictions(
                forecast_id=forecast_id,
                lottery="xyft",
                source="native",
                probabilities_by_strategy={"good": good, "bad": bad},
                weights={"good": 0.5, "bad": 0.5},
            )
            database.save_draws(
                [
                    DrawModel(
                        lottery="xyft",
                        period="200001",
                        numbers=[3, 1, 2, 4, 5, 6, 7, 8, 9, 10],
                    )
                ]
            )
            self.assertEqual(database.settle_forecasts("xyft"), 1)
            weights = database.get_strategy_weights("xyft", "native")
            self.assertGreater(weights["good"], weights["bad"])
            summary = database.strategy_learning_summary("xyft", "native")
            self.assertEqual({item["samples"] for item in summary}, {1})
            self.assertEqual(sum(int(item["top6_hits"]) for item in summary), 1)

    def test_blend_follows_updated_weights(self) -> None:
        left = [0.7] + [0.3 / 9] * 9
        right = [0.3 / 9] * 9 + [0.7]
        blended = blend_strategy_probabilities(
            {"left": left, "right": right},
            {"left": 0.8, "right": 0.2},
        )
        self.assertGreater(blended[0], blended[9])


if __name__ == "__main__":
    unittest.main()
