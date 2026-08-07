from __future__ import annotations

from dataclasses import replace

from . import ai_ensemble, fixed_target_bridge


_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    original = ai_ensemble.analyze_ensemble

    def compatible_analyze(*args, **kwargs):
        result = original(*args, **kwargs)
        analysis = result.analysis
        required = f"固定目标六码{fixed_target_bridge.TARGET_LABEL}"
        if required not in analysis:
            analysis = f"{required}；" + analysis

        strategy_probabilities: dict[str, list[float]] = {}
        strategy_weights: dict[str, float] = {}
        for name, values in result.strategy_probabilities.items():
            normalized_name = name.replace(
                f"ai_fixed_{fixed_target_bridge.TARGET_LABEL}_stable_position_",
                f"ai_fixed_{fixed_target_bridge.TARGET_LABEL}_position_",
            )
            strategy_probabilities[normalized_name] = values
        for name, value in result.strategy_weights.items():
            normalized_name = name.replace(
                f"ai_fixed_{fixed_target_bridge.TARGET_LABEL}_stable_position_",
                f"ai_fixed_{fixed_target_bridge.TARGET_LABEL}_position_",
            )
            strategy_weights[normalized_name] = value

        return replace(
            result,
            analysis=analysis,
            strategy_probabilities=strategy_probabilities,
            strategy_weights=strategy_weights,
        )

    ai_ensemble.analyze_ensemble = compatible_analyze
    _INSTALLED = True
