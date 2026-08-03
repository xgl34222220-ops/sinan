from __future__ import annotations

import unittest

from app.models import DrawModel
from app.predictor import predict


class PredictorTest(unittest.TestCase):
    def history(self, count: int = 160) -> list[DrawModel]:
        draws: list[DrawModel] = []
        for index in range(1, count + 1):
            first = 7 if index > count - 18 and index % 4 != 0 else index % 10 + 1
            numbers = [first] + [number for number in range(1, 11) if number != first]
            draws.append(
                DrawModel(
                    lottery="azxy10",
                    period=str(index).zfill(6),
                    numbers=numbers,
                    draw_time="2026-08-01 00:00:00",
                )
            )
        return draws

    def test_prediction_is_normalized_and_complete(self) -> None:
        result = predict(self.history())
        self.assertEqual(10, len(result.positions))
        self.assertIn(result.selected.position, range(10))
        self.assertEqual(6, len(result.selected.top6))
        self.assertEqual(7, len(result.selected.top7))
        self.assertAlmostEqual(1.0, sum(result.selected.probabilities), places=9)
        self.assertEqual(10, len(set(result.selected.top7 + [
            number for number in range(1, 11) if number not in result.selected.top7
        ])))

    def test_too_little_history_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            predict(self.history(20))


if __name__ == "__main__":
    unittest.main()
