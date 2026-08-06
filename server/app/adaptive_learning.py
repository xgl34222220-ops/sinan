from __future__ import annotations

import math
from typing import Iterable, Mapping

from .models import DrawModel


MATH_STRATEGIES = (
    "long_frequency",
    "recent_frequency",
    "recency_decay",
    "omission_hazard",
    "markov_transition",
    "trend",
    "stability",
)
AI_STRATEGY = "ai_review"
DEFAULT_WEIGHTS = {
    "long_frequency": 0.13,
    "recent_frequency": 0.09,
    "recency_decay": 0.08,
    "omission_hazard": 0.08,
    "markov_transition": 0.13,
    "trend": 0.08,
    "stability": 0.06,
    "ai_review": 0.35,
}
UNIFORM_LOG_LOSS = math.log(10.0)


def normalize_probabilities(values: Iterable[float]) -> list[float]:
    safe = [
        float(value) if math.isfinite(float(value)) and float(value) > 0 else 1e-12
        for value in values
    ]
    if len(safe) != 10:
        raise ValueError("策略必须输出10个号码概率")
    total = sum(safe) or 1.0
    return [value / total for value in safe]


def normalize_strategy_weights(
    current: Mapping[str, float] | None,
    strategies: Iterable[str],
) -> dict[str, float]:
    names = tuple(dict.fromkeys(strategies))
    if not names:
        return {}
    supplied = current or {}
    raw = {
        name: max(0.0, float(supplied.get(name, DEFAULT_WEIGHTS.get(name, 0.08))))
        for name in names
    }
    total = sum(raw.values())
    if total <= 0:
        return {name: 1.0 / len(names) for name in names}
    return {name: value / total for name, value in raw.items()}


def blend_strategy_probabilities(
    components: Mapping[str, list[float]],
    weights: Mapping[str, float] | None,
) -> list[float]:
    if not components:
        raise ValueError("缺少可融合的预测策略")
    normalized_components = {
        name: normalize_probabilities(probabilities)
        for name, probabilities in components.items()
    }
    active = normalize_strategy_weights(weights, normalized_components)
    return normalize_probabilities(
        sum(active[name] * normalized_components[name][index] for name in normalized_components)
        for index in range(10)
    )


def _canonical(history: list[DrawModel], limit: int = 3000) -> list[DrawModel]:
    return [
        draw
        for draw in history
        if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
    ][-limit:]


def _counts(values: list[int], window: int) -> list[float]:
    result = [0.0] * 10
    for number in values[-window:]:
        if 1 <= number <= 10:
            result[number - 1] += 1.0
    return result


def _intervals(values: list[int], number: int) -> tuple[list[int], int]:
    positions = [index for index, value in enumerate(values) if value == number]
    intervals = [positions[index] - positions[index - 1] for index in range(1, len(positions))]
    current_gap = len(values) if not positions else len(values) - 1 - positions[-1]
    return intervals, current_gap


def strategy_components(
    history: list[DrawModel],
    position: int,
    *,
    mask_recent: int = 0,
) -> dict[str, list[float]]:
    verified = _canonical(history)
    if mask_recent > 0:
        if len(verified) - mask_recent < 30:
            raise ValueError("隐藏近期样本后不足30期")
        verified = verified[:-mask_recent]
    if len(verified) < 30:
        raise ValueError("至少需要30期有效历史")
    if position not in range(10):
        raise ValueError("名次超出范围")

    values = [draw.numbers[position] for draw in verified]
    count18 = _counts(values, 18)
    count45 = _counts(values, 45)
    count120 = _counts(values, 120)
    size18 = float(min(18, len(values)))
    size45 = float(min(45, len(values)))
    size120 = float(min(120, len(values)))

    long_frequency = normalize_probabilities(
        (count120[index] + 1.0) / (size120 + 10.0)
        for index in range(10)
    )
    recent_frequency = normalize_probabilities(
        0.62 * (count18[index] + 0.8) / (size18 + 8.0)
        + 0.38 * (count45[index] + 1.2) / (size45 + 12.0)
        for index in range(10)
    )

    recency_raw = [0.0] * 10
    for index, number in enumerate(values):
        age = len(values) - 1 - index
        recency_raw[number - 1] += math.exp(-age / 24.0)
    recency_decay = normalize_probabilities(recency_raw)

    hazard_raw: list[float] = []
    for number in range(1, 11):
        intervals, current_gap = _intervals(values, number)
        if not intervals:
            hazard_raw.append(0.1)
            continue
        bandwidth = max(1, round(math.sqrt(len(intervals)) / 2))
        at_risk = sum(1 for gap in intervals if gap >= max(1, current_gap - bandwidth))
        nearby = sum(1 for gap in intervals if abs(gap - current_gap) <= bandwidth)
        empirical = (nearby + 1.0) / (at_risk + 10.0)
        hazard_raw.append(0.65 * empirical + 0.35 * 0.1)
    omission_hazard = normalize_probabilities(hazard_raw)

    current = values[-1]
    successors = [0.0] * 10
    transition_samples = 0
    for index in range(1, len(values)):
        if values[index - 1] == current:
            successors[values[index] - 1] += 1.0
            transition_samples += 1
    shrink = max(8.0, 24.0 - transition_samples)
    markov_transition = normalize_probabilities(
        successors[index] + long_frequency[index] * shrink
        for index in range(10)
    )

    trend = normalize_probabilities(
        math.exp((count18[index] / size18 - count45[index] / size45) * 4.0)
        for index in range(10)
    )
    stability = normalize_probabilities(
        long_frequency[index]
        / (
            0.06
            + abs(count18[index] / size18 - count45[index] / size45)
            + 0.45 * abs(count45[index] / size45 - count120[index] / size120)
        )
        for index in range(10)
    )
    return {
        "long_frequency": long_frequency,
        "recent_frequency": recent_frequency,
        "recency_decay": recency_decay,
        "omission_hazard": omission_hazard,
        "markov_transition": markov_transition,
        "trend": trend,
        "stability": stability,
    }


def prediction_loss(probabilities: list[float], actual_number: int) -> dict[str, float | bool]:
    normalized = normalize_probabilities(probabilities)
    if actual_number not in range(1, 11):
        raise ValueError("实际号码超出范围")
    actual_index = actual_number - 1
    log_loss = -math.log(max(1e-12, normalized[actual_index]))
    brier = sum(
        (probability - (1.0 if index == actual_index else 0.0)) ** 2
        for index, probability in enumerate(normalized)
    )
    ranked = sorted(range(10), key=normalized.__getitem__, reverse=True)
    return {
        "log_loss": log_loss,
        "brier": brier,
        "top6_hit": actual_index in ranked[:6],
        "combined_loss": 0.8 * log_loss + 0.2 * (brier / 0.9) * UNIFORM_LOG_LOSS,
    }


def _bounded_normalize(
    values: Mapping[str, float],
    *,
    floor: float = 0.025,
    cap: float = 0.55,
) -> dict[str, float]:
    names = tuple(values)
    if not names:
        return {}
    safe = {name: max(1e-12, float(values[name])) for name in names}
    for _ in range(8):
        total = sum(safe.values()) or 1.0
        safe = {name: value / total for name, value in safe.items()}
        low = [name for name, value in safe.items() if value < floor]
        high = [name for name, value in safe.items() if value > cap]
        if not low and not high:
            break
        fixed = {name: floor for name in low}
        fixed.update({name: cap for name in high})
        free = [name for name in names if name not in fixed]
        remaining = max(0.0, 1.0 - sum(fixed.values()))
        free_total = sum(safe[name] for name in free) or 1.0
        safe = {
            name: fixed.get(name, remaining * safe[name] / free_total)
            for name in names
        }
    total = sum(safe.values()) or 1.0
    return {name: value / total for name, value in safe.items()}


def update_strategy_weights(
    current: Mapping[str, float],
    losses: Mapping[str, float],
    *,
    learning_rate: float = 0.22,
) -> dict[str, float]:
    names = tuple(losses)
    weights = normalize_strategy_weights(current, names)
    updated = {
        name: weights[name]
        * math.exp(
            -learning_rate
            * max(-UNIFORM_LOG_LOSS, min(UNIFORM_LOG_LOSS, losses[name] - UNIFORM_LOG_LOSS))
        )
        for name in names
    }
    return _bounded_normalize(updated)
