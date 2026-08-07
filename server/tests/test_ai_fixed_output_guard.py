from __future__ import annotations

import unittest

from app.ai_fixed_output_guard import FIXED_AI_TOP6, _fixed_sets


class AiFixedOutputGuardTest(unittest.TestCase):
    def test_ai_dynamic_numbers_are_rejected_at_output_boundary(self) -> None:
        top6, top7 = _fixed_sets(
            source="ai",
            top6=[2, 5, 4, 10, 1, 8],
            top7=[2, 5, 4, 10, 1, 8, 3],
            probabilities=[0.05, 0.10, 0.08, 0.07, 0.09, 0.06, 0.11, 0.12, 0.15, 0.17],
        )
        self.assertEqual([2, 3, 5, 7, 8, 10], top6)
        self.assertEqual(FIXED_AI_TOP6, top6)
        self.assertEqual([2, 3, 5, 7, 8, 10, 9], top7)

    def test_native_dynamic_prediction_is_left_completely_unchanged(self) -> None:
        original_top6 = [2, 5, 4, 10, 1, 8]
        original_top7 = [2, 5, 4, 10, 1, 8, 3]
        top6, top7 = _fixed_sets(
            source="native",
            top6=original_top6,
            top7=original_top7,
            probabilities=[0.1] * 10,
        )
        self.assertEqual(original_top6, top6)
        self.assertEqual(original_top7, top7)


if __name__ == "__main__":
    unittest.main()
