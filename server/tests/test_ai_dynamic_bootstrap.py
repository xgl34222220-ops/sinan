from __future__ import annotations

import unittest

from app import ai, ai_continual_bridge, ai_ensemble, runtime_patches
from app import ai_fixed_output_guard, ai_position_autonomy_guard
from app import fixed_target_bridge, fixed_target_runtime_guard
from app.db import Database


class AiDynamicBootstrapTest(unittest.TestCase):
    def test_dynamic_continual_ensemble_is_the_active_engine(self) -> None:
        self.assertIs(
            ai_ensemble.analyze_ensemble,
            ai_continual_bridge._analyze_ensemble_with_continual_learning,
        )
        self.assertTrue(ai_continual_bridge._INSTALLED)

    def test_fixed_target_overrides_are_not_installed(self) -> None:
        self.assertFalse(fixed_target_bridge._INSTALLED)
        self.assertFalse(fixed_target_runtime_guard._INSTALLED)
        self.assertFalse(ai_position_autonomy_guard._INSTALLED)
        self.assertFalse(ai_fixed_output_guard._INSTALLED)

    def test_ai_forecast_save_path_is_not_rewritten_to_235780(self) -> None:
        self.assertIsNot(Database.save_forecast, ai_fixed_output_guard._guarded_save_forecast)
        self.assertIsNot(
            Database.save_forecast_with_strategies,
            ai_fixed_output_guard._guarded_save_forecast_with_strategies,
        )

    def test_native_overlap_never_forces_ai_to_change_answer(self) -> None:
        # runtime_patches still supplies the admin/streak accuracy fixes, but its
        # legacy cross-source divergence wrapper is deliberately retired.
        self.assertIs(ai.analyze, runtime_patches._ORIGINAL_AI_ANALYZE)
        self.assertIsNot(ai.analyze, runtime_patches._analyze_with_independence)


if __name__ == "__main__":
    unittest.main()
