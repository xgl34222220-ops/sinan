from __future__ import annotations

from dataclasses import dataclass

from .forecast_quality import position_quality_profile, regularize_recent_copy
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


@dataclass(frozen=True)
class NativePrediction:
    selected: PositionResult
    positions: list[PositionResult]
    analysis: str
    risk_note: str


def _position_result(history: list[DrawModel], position: int) -> PositionResult:
    profile = position_quality_profile(history, position)
    probabilities, guarded = regularize_recent_copy(
        profile.probabilities,
        history,
        position,
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
    )


def predict(history_input: list[DrawModel]) -> NativePrediction:
    history = [
        draw
        for draw in history_input
        if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
    ][-3000:]
    if len(history) < 30:
        raise ValueError("至少需要 30 期有效历史才能生成预测")

    positions = [_position_result(history, position) for position in range(10)]
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
    analysis = (
        f"本机云端引擎对十个名次分别执行滚动前向验证后选择第 {selected.position + 1} 名；"
        f"验证样本 {selected.walk_forward_samples} 期，收缩命中率约 {hit_percent:.1f}%，"
        f"当前六码边界差约 {margin_percent:.2f} 个百分点。"
        + (
            " 检测到结果过度贴近最近六码，已使用隐藏近期窗口和边界正则重新排序。"
            if selected.copy_guard_applied
            else ""
        )
    )
    risk_note = (
        "随机开奖没有可保证的可预测规律；滚动验证只能约束算法不凭单期结果拍脑袋。"
        "候选结果不得理解为必中或真实中奖概率。"
    )
    return NativePrediction(selected, positions, analysis, risk_note)
