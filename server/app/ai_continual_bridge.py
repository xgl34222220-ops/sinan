from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, replace
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
_ORIGINAL_POSITION_REVIEW = ai_ensemble._position_review
_ORIGINAL_AGGREGATE = ai_ensemble._aggregate
_POSITION_PROFILES: ContextVar[tuple[ContinualPositionProfile, ...] | None] = ContextVar(
    "tianji_ai_position_profiles",
    default=None,
)
_AI_POSITION_WEIGHT = 0.38
_LEARNED_POSITION_WEIGHT = 0.62
_AI_PIPELINE_NAMESPACE = "ai_v2_position"
_STATISTICAL_PRIOR_SUFFIX = "forward_statistical_prior"


@dataclass(frozen=True)
class _TaggedPositionReview:
    scores: list[float]
    analysis: str
    usage: dict[str, int]
    _tianji_position_review: bool = True


def _strategy_prefix(position: int) -> str:
    return f"{_AI_PIPELINE_NAMESPACE}_{position + 1}:"


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


def statistical_prior_weight(profile: ContinualPositionProfile) -> float:
    """Seed the number-level statistical prior from out-of-sample evidence.

    The value is only an initial weight. After forecasts settle the database
    learns this strategy exactly like every AI reviewer and can raise or lower
    it from real log-loss/Brier/Top6 performance.
    """
    samples = max(0, int(profile.walk_forward_samples))
    reliability = min(1.0, samples / 60.0)
    hit_edge = max(-0.10, min(0.10, float(profile.walk_forward_hit_rate) - 0.60))
    loss_edge = max(
        -0.20,
        min(
            0.20,
            (UNIFORM_LOG_LOSS - float(profile.average_log_loss)) / UNIFORM_LOG_LOSS,
        ),
    )
    weight = 0.24 + reliability * (hit_edge * 1.40 + loss_edge * 0.45)
    if profile.max_miss_streak > 8:
        weight -= min(0.08, (profile.max_miss_streak - 8) * 0.012)
    if _profile_passed(profile):
        weight = max(weight, 0.40)
    return max(0.16, min(0.46, weight))


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
        "number_statistical_prior_seed_weight": round(statistical_prior_weight(profile), 6),
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


def _position_review_with_learning_tag(*args: Any, **kwargs: Any) -> _TaggedPositionReview:
    result = _ORIGINAL_POSITION_REVIEW(*args, **kwargs)
    return _TaggedPositionReview(
        scores=list(result.scores),
        analysis=str(result.analysis),
        usage=dict(result.usage),
    )


def _aggregate_with_position_learning(results: list[Any]) -> list[float]:
    """Calibrate position votes only; number votes must remain number votes.

    The old bridge keyed solely on vector length. Position scores and number
    scores both contain ten values, so number aggregation was silently polluted
    by position-level forward profiles. Position reviews are now explicitly
    tagged at their source and only those tagged reviews receive position
    calibration.
    """
    ai_scores = _ORIGINAL_AGGREGATE(results)
    if not results or not all(
        bool(getattr(result, "_tianji_position_review", False))
        for result in results
    ):
        return ai_scores
    profiles = _POSITION_PROFILES.get()
    if profiles is None:
        return ai_scores
    return blend_position_scores(ai_scores, profiles)


def position_strategy_probabilities(
    position: int,
    probabilities: dict[str, list[float]],
    statistical_prior: list[float] | None = None,
) -> dict[str, list[float]]:
    prefix = _strategy_prefix(position)
    result = {
        f"{prefix}{name.removeprefix('ai_')}": list(values)
        for name, values in probabilities.items()
    }
    if statistical_prior is not None and len(statistical_prior) == 10:
        result[f"{prefix}{_STATISTICAL_PRIOR_SUFFIX}"] = list(statistical_prior)
    return result


def position_strategy_weights(
    position: int,
    probabilities: dict[str, list[float]],
    learned: dict[str, float] | None,
) -> dict[str, float]:
    """Reviewer-only weighting kept for direct compatibility tests."""
    namespaced = position_strategy_probabilities(position, probabilities)
    supplied = learned or {}
    active = {
        name: float(supplied[name])
        for name in namespaced
        if name in supplied
    }
    return normalize_strategy_weights(active, namespaced)


def _hybrid_strategy_weights(
    position: int,
    probabilities_by_strategy: dict[str, list[float]],
    learned: dict[str, float] | None,
    profile: ContinualPositionProfile,
) -> dict[str, float]:
    prefix = _strategy_prefix(position)
    statistical_name = f"{prefix}{_STATISTICAL_PRIOR_SUFFIX}"
    supplied = learned or {}

    # v2 deliberately ignores generic/legacy AI strategy names. Old fixed-target
    # and cross-position learning is preserved in the database for audit but is
    # not allowed to seed the rebuilt predictor.
    if statistical_name in supplied:
        active = {
            name: float(supplied[name])
            for name in probabilities_by_strategy
            if name in supplied
        }
        return normalize_strategy_weights(active, probabilities_by_strategy)

    reviewer_names = [
        name for name in probabilities_by_strategy if name != statistical_name
    ]
    reviewer_active = {
        name: float(supplied[name])
        for name in reviewer_names
        if name in supplied
    }
    reviewer_weights = normalize_strategy_weights(reviewer_active, reviewer_names)

    statistical_weight = statistical_prior_weight(profile)
    remaining = max(0.0, 1.0 - statistical_weight)
    weights = {
        name: reviewer_weights[name] * remaining
        for name in reviewer_names
    }
    weights[statistical_name] = statistical_weight
    return weights


def _apply_position_specific_number_learning(
    result: Any,
    learned: dict[str, float] | None,
    profile: ContinualPositionProfile | None = None,
) -> Any:
    position = int(result.position)
    statistical_prior = profile.probabilities if profile is not None else None
    probabilities_by_strategy = position_strategy_probabilities(
        position,
        result.strategy_probabilities,
        statistical_prior,
    )
    if profile is None:
        weights = position_strategy_weights(
            position,
            result.strategy_probabilities,
            learned,
        )
    else:
        weights = _hybrid_strategy_weights(
            position,
            probabilities_by_strategy,
            learned,
            profile,
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

    selected = profiles[int(result.position)]
    result = _apply_position_specific_number_learning(
        result,
        strategy_weights,
        selected,
    )
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
    )[:4]
    reviewer_text = "、".join(
        f"{name} {weight * 100:.1f}%" for name, weight in reviewer_leaders
    )
    statistical_name = f"{_strategy_prefix(selected.position)}{_STATISTICAL_PRIOR_SUFFIX}"
    statistical_weight = float(result.strategy_weights.get(statistical_name, 0.0))
    evidence_text = (
        "通过外样本证据门槛"
        if selected_passed
        else "未通过强信号门槛，仅作为弱证据观察结果"
    )
    base_analysis = str(result.analysis).replace(
        " AI预测不再混入本地频率、遗漏、马尔可夫、趋势或稳定性策略。",
        " AI评审阶段不读取本地模型最终六码。",
    )
    analysis = (
        f"{base_analysis} 名次决策已接入持续学习校准：十个名次分别用已结算历史做滚动前向验证，"
        f"本轮有 {passed_count} 个名次通过门槛；第 {selected.position + 1} 名验证 "
        f"{selected.walk_forward_samples} 期，六码命中率约 {selected.walk_forward_hit_rate * 100:.1f}%，"
        f"相对随机基准超额 {selected.excess_hit_rate * 100:+.1f} 个百分点，"
        f"最长连续未中 {selected.max_miss_streak} 期，{evidence_text}。"
        f"号码层改为动态混合：AI匿名评审 + 该名次独立前向统计先验；"
        f"统计先验当前权重约 {statistical_weight * 100:.1f}%，之后与AI评审一样按真实结算损失自动升降。"
        f"该名次当前主要统计策略：{leader_text}；v2最终号码策略：{reviewer_text}。"
        "v2使用独立学习命名空间，不继承旧固定池权重；AI不会读取或复制本地模型最终六码，"
        "也不会为了与本地不同而强制改号。"
    )[:1520]
    risk_note = (
        f"{result.risk_note} AI名次评分由真实前向成绩校准；号码层的AI评审和统计先验分别保存v2策略快照，"
        "开奖后按LogLoss、Brier与Top6真实结果持续调权。旧固定池/旧跨名次权重不进入v2融合。"
        "持续学习只能压制已观察到的弱策略，不能把随机开奖变成可保证预测。"
    )[:860]
    return replace(result, analysis=analysis, risk_note=risk_note)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ai_ensemble.build_position_evidence = _build_position_evidence_with_learning
    ai_ensemble._position_review = _position_review_with_learning_tag
    ai_ensemble._aggregate = _aggregate_with_position_learning
    ai_ensemble.analyze_ensemble = _analyze_ensemble_with_continual_learning
    _INSTALLED = True
