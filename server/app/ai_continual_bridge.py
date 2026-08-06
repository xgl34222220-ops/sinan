from __future__ import annotations

from contextvars import ContextVar
from dataclasses import replace
import math
from typing import Any

from . import ai_ensemble
from .adaptive_learning import (
    UNIFORM_LOG_LOSS,
    blend_strategy_probabilities,
    normalize_strategy_weights,
)
from .continual_learning import ContinualPositionProfile, build_position_profile


_INSTALLED = False
_ORIGINAL_ANALYZE_ENSEMBLE = ai_ensemble.analyze_ensemble
_ORIGINAL_BUILD_POSITION_EVIDENCE = ai_ensemble.build_position_evidence
_ORIGINAL_AGGREGATE = ai_ensemble._aggregate
_POSITION_PROFILES: ContextVar[tuple[ContinualPositionProfile, ...] | None] = ContextVar(
    "tianji_ai_position_profiles",
    default=None,
)
_AI_POSITION_WEIGHT = 0.38
_LEARNED_POSITION_WEIGHT = 0.62


def _profile_passed(profile: ContinualPositionProfile) -> bool:
    return bool(
        profile.walk_forward_samples >= 24
        and profile.walk_forward_hit_rate >= 0.615
        and profile.average_log_loss <= UNIFORM_LOG_LOSS * 1.01
        and profile.max_miss_streak <= 8
    )


def _learning_score(profile: ContinualPositionProfile) -> float:
    hit_edge = max(-0.25, min(0.25, profile.excess_hit_rate))
    loss_edge = max(
        -0.35,
        min(
            0.35,
            (UNIFORM_LOG_LOSS - profile.average_log_loss) / UNIFORM_LOG_LOSS,
        ),
    )
    boundary = max(0.0, min(0.04, profile.boundary_margin))
    streak_penalty = max(0, profile.max_miss_streak - 3) * 0.08
    pass_bonus = 0.35 if _profile_passed(profile) else 0.0
    return math.exp(
        hit_edge * 8.0
        + loss_edge * 2.2
        + boundary * 5.0
        + pass_bonus
        - streak_penalty
    )


def _normalize(values: list[float]) -> list[float]:
    safe = [
        float(value) if math.isfinite(float(value)) and float(value) > 0 else 1e-12
        for value in values
    ]
    total = sum(safe) or 1.0
    return [value / total for value in safe]


def blend_position_scores(
    ai_scores: list[float],
    profiles: tuple[ContinualPositionProfile, ...],
) -> list[float]:
    """Combine AI judgement with independently measured forward performance.

    AI never receives the native model's final top6. It only gets settled,
    out-of-sample position metrics. When at least one position clears the
    minimum evidence gate, weak positions are prevented from winning solely
    because one language-model review produced an extreme score.
    """
    if len(ai_scores) != 10 or len(profiles) != 10:
        return _normalize(ai_scores)

    passed = [_profile_passed(profile) for profile in profiles]
    has_passed = any(passed)
    learned_raw = [_learning_score(profile) for profile in profiles]
    if has_passed:
        learned_raw = [
            score if passed[index] else score * 0.12
            for index, score in enumerate(learned_raw)
        ]
    learned = _normalize(learned_raw)
    ai_normalized = _normalize(ai_scores)
    blended = [
        ai_normalized[index] * _AI_POSITION_WEIGHT
        + learned[index] * _LEARNED_POSITION_WEIGHT
        for index in range(10)
    ]
    if has_passed:
        blended = [
            value if passed[index] else value * 0.20
            for index, value in enumerate(blended)
        ]
    return _normalize(blended)


def position_learning_payload(profile: ContinualPositionProfile) -> dict[str, Any]:
    leaders = sorted(
        profile.strategy_weights.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:4]
    return {
        "forward_samples": profile.walk_forward_samples,
        "top6_hit_rate": round(profile.walk_forward_hit_rate, 6),
        "excess_over_random_top6": round(profile.excess_hit_rate, 6),
        "average_log_loss": round(profile.average_log_loss, 6),
        "uniform_log_loss_baseline": round(UNIFORM_LOG_LOSS, 6),
        "max_miss_streak": profile.max_miss_streak,
        "validation_score": round(profile.validation_score, 6),
        "evidence_gate_passed": _profile_passed(profile),
        "leading_learned_strategies": [
            {"strategy": name, "weight": round(weight, 6)}
            for name, weight in leaders
        ],
    }


def _build_position_evidence_with_learning(
    history: list[Any],
) -> list[dict[str, Any]]:
    evidence = _ORIGINAL_BUILD_POSITION_EVIDENCE(history)
    profiles = _POSITION_PROFILES.get()
    if profiles is None or len(profiles) != len(evidence):
        return evidence
    return [
        {
            **item,
            "settled_forward_learning": position_learning_payload(profiles[index]),
        }
        for index, item in enumerate(evidence)
    ]


def _aggregate_with_position_learning(results: list[Any]) -> list[float]:
    ai_scores = _ORIGINAL_AGGREGATE(results)
    profiles = _POSITION_PROFILES.get()
    if profiles is None:
        return ai_scores
    return blend_position_scores(ai_scores, profiles)


def position_strategy_probabilities(
    position: int,
    probabilities: dict[str, list[float]],
) -> dict[str, list[float]]:
    prefix = f"position_{position + 1}:"
    return {
        f"{prefix}{name}": values
        for name, values in probabilities.items()
    }


def position_strategy_weights(
    position: int,
    probabilities: dict[str, list[float]],
    learned: dict[str, float] | None,
) -> dict[str, float]:
    namespaced = position_strategy_probabilities(position, probabilities)
    supplied = learned or {}
    active = {
        name: float(supplied[name])
        for name in namespaced
        if name in supplied
    }
    if not active:
        prefix = f"position_{position + 1}:"
        active = {
            namespaced_name: float(supplied.get(namespaced_name.removeprefix(prefix), 0.0))
            for namespaced_name in namespaced
            if namespaced_name.removeprefix(prefix) in supplied
        }
    return normalize_strategy_weights(active, namespaced)


def _apply_position_specific_number_learning(
    result: Any,
    learned: dict[str, float] | None,
) -> Any:
    probabilities_by_strategy = position_strategy_probabilities(
        int(result.position),
        result.strategy_probabilities,
    )
    weights = position_strategy_weights(
        int(result.position),
        result.strategy_probabilities,
        learned,
    )
    probabilities = blend_strategy_probabilities(
        probabilities_by_strategy,
        weights,
    )
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
    return replace(
        result,
        probabilities=probabilities,
        top6=[index + 1 for index in ranked[:6]],
        top7=[index + 1 for index in ranked[:7]],
        strategy_probabilities=probabilities_by_strategy,
        strategy_weights=weights,
    )


def _analyze_ensemble_with_continual_learning(
    history: list[Any],
    target_period: str,
    config: Any,
    *,
    recent_positions: list[int] | None = None,
    strategy_weights: dict[str, float] | None = None,
) -> Any:
    verified = [
        draw
        for draw in history
        if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
    ][-120:]
    if len(verified) < 30:
        return _ORIGINAL_ANALYZE_ENSEMBLE(
            history,
            target_period,
            config,
            recent_positions=recent_positions,
            strategy_weights=strategy_weights,
        )

    profiles = tuple(
        build_position_profile(
            verified,
            position,
            max_validation_samples=48,
        )
        for position in range(10)
    )
    token = _POSITION_PROFILES.set(profiles)
    try:
        result = _ORIGINAL_ANALYZE_ENSEMBLE(
            history,
            target_period,
            config,
            recent_positions=recent_positions,
            strategy_weights=strategy_weights,
        )
    finally:
        _POSITION_PROFILES.reset(token)

    result = _apply_position_specific_number_learning(result, strategy_weights)
    selected = profiles[int(result.position)]
    passed_count = sum(_profile_passed(profile) for profile in profiles)
    selected_passed = _profile_passed(selected)
    leaders = sorted(
        selected.strategy_weights.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    leader_text = "、".join(
        f"{name} {weight * 100:.1f}%" for name, weight in leaders
    )
    reviewer_leaders = sorted(
        result.strategy_weights.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    reviewer_text = "、".join(
        f"{name} {weight * 100:.1f}%" for name, weight in reviewer_leaders
    )
    evidence_text = (
        "通过外样本证据门槛"
        if selected_passed
        else "未通过强信号门槛，仅作为弱证据观察结果"
    )
    analysis = (
        f"{result.analysis} 名次决策已接入持续学习校准：十个名次分别用已结算历史做滚动前向验证，"
        f"本轮有 {passed_count} 个名次通过门槛；第 {selected.position + 1} 名验证 "
        f"{selected.walk_forward_samples} 期，六码命中率约 {selected.walk_forward_hit_rate * 100:.1f}%，"
        f"相对随机基准超额 {selected.excess_hit_rate * 100:+.1f} 个百分点，"
        f"最长连续未中 {selected.max_miss_streak} 期，{evidence_text}。"
        f"该名次当前主要结构策略：{leader_text}；AI号码评审按名次独立学习：{reviewer_text}。"
        "AI未读取本地模型最终六码。"
    )[:1150]
    risk_note = (
        f"{result.risk_note} AI名次评分现由真实前向成绩校准，号码评审权重按具体名次分别结算；"
        "持续学习代表随已结算样本更新和淘汰无效策略，不代表准确率能够单调上升。"
    )[:680]
    return replace(result, analysis=analysis, risk_note=risk_note)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ai_ensemble.build_position_evidence = _build_position_evidence_with_learning
    ai_ensemble._aggregate = _aggregate_with_position_learning
    ai_ensemble.analyze_ensemble = _analyze_ensemble_with_continual_learning
    _INSTALLED = True
