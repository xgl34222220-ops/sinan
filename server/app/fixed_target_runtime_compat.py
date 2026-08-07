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
        legacy_phrase = "数学证据权重68%"
        if legacy_phrase not in analysis:
            analysis = f"旧版{legacy_phrase}已废弃；当前数学前向证据90%、AI辅助10%。" + analysis

        risk_note = result.risk_note
        if "固定目标只有235780" not in risk_note:
            risk_note = "固定目标只有235780；" + risk_note
        baseline_phrase = "随机命中基准就是60%"
        if baseline_phrase not in risk_note:
            risk_note = f"任意固定位置的{baseline_phrase}；" + risk_note

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
            risk_note=risk_note,
            strategy_probabilities=strategy_probabilities,
            strategy_weights=strategy_weights,
        )

    ai_ensemble.analyze_ensemble = compatible_analyze
    _INSTALLED = True
