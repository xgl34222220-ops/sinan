from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

path = ROOT / "server/app/ai_ensemble.py"
text = path.read_text(encoding="utf-8")
old = '''    primary_ai_probabilities = _aggregate(number_results)
    objective_probabilities = statistical_probabilities(verified, selected_position)
    primary_probabilities = blend_validated_probabilities(
        primary_ai_probabilities,
        objective_probabilities,
        secondary_weight=0.45,
    )
    probabilities = primary_probabilities
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)

    recent_copy_reviewed = _matches_recent_window(
        ranked,
        verified,
        selected_position,
    )
    copy_guard_applied = False
'''
new = '''    primary_ai_probabilities = _aggregate(number_results)
    raw_ai_ranked = sorted(
        range(10),
        key=primary_ai_probabilities.__getitem__,
        reverse=True,
    )
    objective_probabilities = statistical_probabilities(verified, selected_position)
    primary_probabilities = blend_validated_probabilities(
        primary_ai_probabilities,
        objective_probabilities,
        secondary_weight=0.45,
    )
    probabilities = primary_probabilities
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)

    raw_copy = recent_copy_diagnostics(raw_ai_ranked, verified, selected_position)
    final_copy = recent_copy_diagnostics(ranked, verified, selected_position)
    ai_score_spread = max(primary_ai_probabilities) - min(primary_ai_probabilities)
    final_boundary = probabilities[ranked[5]] - probabilities[ranked[6]]
    recent_copy_reviewed = (
        (ai_score_spread >= 0.02 and raw_copy.triggered)
        or final_copy.exact_latest_six
        or (final_copy.triggered and final_boundary >= 0.004)
    )
    copy_guard_applied = False
'''
if old not in text:
    raise SystemExit("primary copy detection block not found")
path.write_text(text.replace(old, new), encoding="utf-8")

test_path = ROOT / "server/tests/test_ai_ensemble.py"
test = test_path.read_text(encoding="utf-8")
test = test.replace(
    '        self.assertIn("完整历史评审与留出评审加权汇总", result.analysis)\n',
    '        self.assertIn("避免直接复制最新六码", result.analysis)\n',
)
test = test.replace(
    '        self.assertIn("未人为强制轮换", result.analysis)\n',
    '        self.assertIn("不再机械锁死", result.analysis)\n',
)
test = test.replace(
    '    def test_final_prediction_is_aggregated_from_ai_reviews_only(\n',
    '    def test_final_prediction_blends_ai_with_forward_validation(\n',
)
test_path.write_text(test, encoding="utf-8")

prefix_path = ROOT / "server/tests/test_ai_prefix_cache.py"
prefix = prefix_path.read_text(encoding="utf-8")
prefix = prefix.replace(
    "from __future__ import annotations\n\nimport unittest\n",
    "from __future__ import annotations\n\nfrom types import SimpleNamespace\nimport unittest\n",
)
prefix = prefix.replace(
    '    @patch("app.ai_ensemble._number_review")\n'
    '    @patch("app.ai_ensemble._position_review")\n'
    '    def test_ensemble_aggregates_usage_without_changing_reviewer_count(\n'
    '        self,\n'
    '        position_review: object,\n'
    '        number_review: object,\n'
    '    ) -> None:\n',
    '    @patch("app.ai_ensemble.recent_copy_diagnostics")\n'
    '    @patch("app.ai_ensemble._number_review")\n'
    '    @patch("app.ai_ensemble._position_review")\n'
    '    def test_ensemble_aggregates_usage_without_changing_reviewer_count(\n'
    '        self,\n'
    '        position_review: object,\n'
    '        number_review: object,\n'
    '        copy_diagnostics: object,\n'
    '    ) -> None:\n'
    '        copy_diagnostics.return_value = SimpleNamespace(\n'
    '            triggered=False,\n'
    '            exact_latest_six=False,\n'
    '        )\n',
)
prefix_path.write_text(prefix, encoding="utf-8")

for relative in (
    ".github/workflows/repair-prediction-degeneracy.yml",
    ".github/workflows/refine-prediction-degeneracy.yml",
    "tools/repair_prediction_degeneracy.py",
    "tools/refine_prediction_degeneracy.py",
):
    (ROOT / relative).unlink(missing_ok=True)
