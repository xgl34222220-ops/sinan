from __future__ import annotations

from dataclasses import dataclass
import math

from .models import DrawModel


@dataclass(frozen=True)
class PositionResult:
    position: int
    probabilities: list[float]
    top6: list[int]
    top7: list[int]
    boundary_margin: float


@dataclass(frozen=True)
class NativePrediction:
    selected: PositionResult
    positions: list[PositionResult]
    analysis: str
    risk_note: str


def _normalize(values: list[float]) -> list[float]:
    safe = [value if math.isfinite(value) and value > 0 else 1e-12 for value in values]
    total = sum(safe) or 1.0
    return [value / total for value in safe]


def _counts(values: list[int], window: int) -> list[float]:
    result = [0.0] * 10
    for number in values[-window:]:
        if 1 <= number <= 10:
            result[number - 1] += 1.0
    return result


def _position_result(history: list[DrawModel], position: int) -> PositionResult:
    values = [draw.numbers[position] for draw in history if len(draw.numbers) == 10]
    if not values:
        raise ValueError("没有可用于预测的开奖历史")

    count20 = _counts(values, 20)
    count60 = _counts(values, 60)
    count120 = _counts(values, 120)
    size20 = float(max(1, min(20, len(values))))
    size60 = float(max(1, min(60, len(values))))
    size120 = float(max(1, min(120, len(values))))

    bayes = _normalize([(count120[index] + 1.0) / (size120 + 10.0) for index in range(10)])

    recency_raw = [0.0] * 10
    for index, number in enumerate(values):
        age = len(values) - 1 - index
        if 1 <= number <= 10:
            recency_raw[number - 1] += math.exp(-age / 15.0)
    recency = _normalize(recency_raw)

    omission_raw: list[float] = []
    for number in range(1, 11):
        latest_index = -1
        for index in range(len(values) - 1, -1, -1):
            if values[index] == number:
                latest_index = index
                break
        gap = len(values) if latest_index < 0 else len(values) - 1 - latest_index
        omission_raw.append(0.45 + math.exp(-abs(gap - 9.0) / 7.0))
    omission = _normalize(omission_raw)

    global_prior = _normalize([value + 1.0 for value in count120])
    current = values[-1]
    successors = [0.0] * 10
    transition_samples = 0
    for index in range(1, len(values)):
        if values[index - 1] == current and 1 <= values[index] <= 10:
            successors[values[index] - 1] += 1.0
            transition_samples += 1
    shrink = max(5.0, 18.0 - transition_samples)
    transition = _normalize(
        [successors[index] + global_prior[index] * shrink for index in range(10)]
    )

    trend = _normalize(
        [
            math.exp((count20[index] / size20 - count60[index] / size60) * 7.0)
            for index in range(10)
        ]
    )

    stability = _normalize(
        [
            1.0
            / (
                0.04
                + abs(count20[index] / size20 - count60[index] / size60)
                + 0.6 * abs(count60[index] / size60 - count120[index] / size120)
            )
            for index in range(10)
        ]
    )

    short_medium_drift = sum(
        abs(count20[index] / size20 - count60[index] / size60) for index in range(10)
    ) / 10.0
    medium_long_drift = sum(
        abs(count60[index] / size60 - count120[index] / size120) for index in range(10)
    ) / 10.0
    drift_strength = min(1.0, max(0.0, short_medium_drift * 12.0))
    stability_strength = min(
        1.0,
        max(0.0, 1.0 - (short_medium_drift + medium_long_drift) * 8.0),
    )
    transition_confidence = min(1.0, transition_samples / 14.0)
    weights = _normalize(
        [
            1.0 + stability_strength * 0.8,
            1.0 + drift_strength * 2.0,
            0.62,
            0.75 + transition_confidence * 1.35,
            0.9 + drift_strength * 2.5,
            0.9 + stability_strength * 1.5,
        ]
    )
    factors = [bayes, recency, omission, transition, trend, stability]
    probabilities = _normalize(
        [
            sum(factors[factor][number] * weights[factor] for factor in range(6))
            for number in range(10)
        ]
    )
    ranked = sorted(range(10), key=lambda index: probabilities[index], reverse=True)
    top6 = [index + 1 for index in ranked[:6]]
    top7 = [index + 1 for index in ranked[:7]]
    boundary_margin = probabilities[ranked[5]] - probabilities[ranked[6]]
    return PositionResult(position, probabilities, top6, top7, boundary_margin)


def predict(history_input: list[DrawModel]) -> NativePrediction:
    history = [draw for draw in history_input if len(draw.numbers) == 10][-3000:]
    if len(history) < 30:
        raise ValueError("至少需要 30 期有效历史才能生成预测")
    positions = [_position_result(history, position) for position in range(10)]
    selected = max(
        positions,
        key=lambda item: (item.boundary_margin, max(item.probabilities) - min(item.probabilities)),
    )
    margin_percent = selected.boundary_margin * 100.0
    analysis = (
        f"本机云端引擎比较十个名次后选择第 {selected.position + 1} 名；"
        f"六码边界差约 {margin_percent:.2f} 个百分点。"
        "评分综合贝叶斯长窗、近期衰减、非单调遗漏、收缩转移、短中窗变化和稳定性。"
    )
    risk_note = (
        "随机开奖不能可靠预测；结果只用于真实前向记录与回测。"
        "边界差较小时应视为弱信号，不得理解为必中或真实中奖概率。"
    )
    return NativePrediction(selected, positions, analysis, risk_note)
