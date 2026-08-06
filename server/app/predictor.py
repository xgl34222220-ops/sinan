from __future__ import annotations

from dataclasses import dataclass, field
import math

from .continual_learning import (
    build_position_profile,
    regularize_continual_recent_copy,
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
    average_log_loss: float = math.log(10.0)
    excess_hit_rate: float = 0.0
    max_miss_streak: int = 0
    evidence_passed: bool = False
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
    profile = build_position_profile(
        history,
        position,
        fallback_weights=strategy_weights,
    )
    probabilities, guarded = regularize_continual_recent_copy(
        profile.probabilities,
        history,
        position,
        strategy_weights=profile.strategy_weights,
    )
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
    average_log_loss = profile.average_log_loss
    evidence_passed = bool(
        profile.walk_forward_samples >= 24
        and profile.walk_forward_hit_rate >= 0.615
        and average_log_loss <= math.log(10.0) * 1.01
        and profile.max_miss_streak <= 8
    )
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
        average_log_loss=average_log_loss,
        excess_hit_rate=profile.excess_hit_rate,
        max_miss_streak=profile.max_miss_streak,
        evidence_passed=evidence_passed,
        strategy_probabilities=profile.strategy_probabilities,
        strategy_weights=profile.strategy_weights,
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
            int(item.evidence_passed),
            item.validation_score,
            item.walk_forward_hit_rate,
            item.boundary_margin,
            -item.max_miss_streak,
        ),
    )
    hit_percent = selected.walk_forward_hit_rate * 100.0
    edge_percent = selected.excess_hit_rate * 100.0
    margin_percent = selected.boundary_margin * 100.0
    leaders = sorted(
        selected.strategy_weights.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:4]
    leader_text = "、".join(
        f"{name} {weight * 100:.1f}%" for name, weight in leaders
    )
    evidence_text = (
        "已通过最低外样本优势门槛"
        if selected.evidence_passed
        else "尚未通过强信号门槛，本期仅作为观察候选"
    )
    analysis = (
        "持续学习引擎对十个名次分别建立独立策略权重，并使用留出样本做前向验证后选择第 "
        f"{selected.position + 1} 名；验证 {selected.walk_forward_samples} 期，"
        f"收缩六码命中率约 {hit_percent:.1f}%，相对随机六码基准的超额约 "
        f"{edge_percent:+.1f} 个百分点，最长连续未中 {selected.max_miss_streak} 期，"
        f"当前六码边界差约 {margin_percent:.2f} 个百分点。"
        "系统同时学习频率、遗漏、转移、趋势、稳定性、012 路、奇偶、大小和万能码结构，"
        f"每期开奖后按真实损失重新分配该名次的策略权重；当前主要策略：{leader_text}。"
        f"{evidence_text}。"
        + (
            " 检测到结果过度贴近最近六码，已隐藏近期样本并重新排序。"
            if selected.copy_guard_applied
            else ""
        )
    )
    risk_note = (
        "这是可持续更新的前向学习系统，不是保证越来越准的神经网络。随机开奖可能长期没有稳定优势；"
        "当外样本证据不足时系统会明确标记为观察候选，而不是伪造高置信度。候选号码不得理解为必中。"
    )
    return NativePrediction(selected, positions, analysis, risk_note)
