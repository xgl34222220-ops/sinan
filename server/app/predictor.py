from __future__ import annotations

from dataclasses import dataclass, field

from .adaptive_learning import normalize_strategy_weights
from .forecast_quality import (
    position_quality_profile,
    regularize_recent_copy,
    statistical_components,
)
from .models import DrawModel


@dataclass(frozen=True)
class PositionResult:
    position: int
    probabilities: list[float]
    top6: list[int]
    top7: list[int]
    boundary_margin: float
    walk_forward_samples: int
    walk_forward_hit_rate: float
    validation_score: float
    copy_guard_applied: bool
    strategy_probabilities: dict[str, list[float]] = field(default_factory=dict)
    strategy_weights: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class NativePrediction:
    selected: PositionResult
    positions: list[PositionResult]
    analysis: str
    risk_note: str


def _position_result(
    history: list[DrawModel],
    position: int,
    strategy_weights: dict[str, float] | None,
) -> PositionResult:
    components = statistical_components(history, position)
    active_weights = normalize_strategy_weights(strategy_weights, components)
    profile = position_quality_profile(
        history,
        position,
        strategy_weights=active_weights,
    )
    probabilities, guarded = regularize_recent_copy(
        profile.probabilities,
        history,
        position,
        strategy_weights=active_weights,
    )
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
    return PositionResult(
        position=position,
        probabilities=probabilities,
        top6=[index + 1 for index in ranked[:6]],
        top7=[index + 1 for index in ranked[:7]],
        boundary_margin=probabilities[ranked[5]] - probabilities[ranked[6]],
        walk_forward_samples=profile.walk_forward_samples,
        walk_forward_hit_rate=profile.walk_forward_hit_rate,
        validation_score=profile.validation_score,
        copy_guard_applied=guarded,
        strategy_probabilities=components,
        strategy_weights=active_weights,
    )


def predict(
    history_input: list[DrawModel],
    strategy_weights: dict[str, float] | None = None,
) -> NativePrediction:
    history = [
        draw
        for draw in history_input
        if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
    ][-3000:]
    if len(history) < 30:
        raise ValueError("至少需要 30 期有效历史才能生成预测")

    positions = [
        _position_result(history, position, strategy_weights)
        for position in range(10)
    ]
    selected = max(
        positions,
        key=lambda item: (
            item.validation_score,
            item.walk_forward_hit_rate,
            item.boundary_margin,
        ),
    )
    hit_percent = selected.walk_forward_hit_rate * 100.0
    margin_percent = selected.boundary_margin * 100.0
    leaders = sorted(
        selected.strategy_weights.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    leader_text = "、".join(f"{name} {weight * 100:.1f}%" for name, weight in leaders)
    analysis = (
        f"自适应云端引擎对十个名次分别执行滚动前向验证后选择第 {selected.position + 1} 名；"
        f"验证样本 {selected.walk_forward_samples} 期，收缩命中率约 {hit_percent:.1f}%，"
        f"当前六码边界差约 {margin_percent:.2f} 个百分点。"
        f"策略权重由每期开奖后的真实损失在线更新，当前主要策略：{leader_text}。"
        + (
            " 检测到结果过度贴近最近六码，已使用隐藏近期窗口和边界正则重新排序。"
            if selected.copy_guard_applied
            else ""
        )
    )
    risk_note = (
        "随机开奖没有可保证的可预测规律；在线学习只会根据真实前向结果调整策略权重，"
        "不能把随机波动变成确定规律。候选结果不得理解为必中或真实中奖概率。"
    )
    return NativePrediction(selected, positions, analysis, risk_note)
