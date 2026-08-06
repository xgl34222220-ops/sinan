from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .adaptive_learning import (
    UNIFORM_LOG_LOSS,
    blend_strategy_probabilities,
    normalize_strategy_weights,
    prediction_loss,
    strategy_components,
)
from .models import DrawModel


STRUCTURAL_STRATEGIES = (
    "route012",
    "parity_structure",
    "size_structure",
    "universal_pool",
)

# Traditional 0-9 universal-six pools adapted to the 1-10 domain by mapping 0 -> 10.
UNIVERSAL_POOLS: dict[int, tuple[int, ...]] = {
    10: (10, 1, 2, 3, 4, 6),
    1: (10, 1, 2, 3, 5, 9),
    2: (10, 1, 2, 4, 8, 9),
    3: (10, 1, 3, 7, 8, 9),
    4: (10, 2, 6, 7, 8, 9),
    5: (10, 4, 5, 6, 7, 8),
    6: (1, 2, 3, 4, 5, 7),
    7: (1, 5, 6, 7, 8, 9),
    8: (2, 3, 4, 5, 6, 8),
    9: (3, 4, 5, 6, 7, 9),
}


@dataclass(frozen=True)
class ContinualPositionProfile:
    position: int
    probabilities: list[float]
    top6: list[int]
    top7: list[int]
    boundary_margin: float
    walk_forward_samples: int
    walk_forward_hits: int
    walk_forward_hit_rate: float
    average_log_loss: float
    validation_score: float
    excess_hit_rate: float
    max_miss_streak: int
    strategy_probabilities: dict[str, list[float]]
    strategy_weights: dict[str, float]


def _canonical(history: list[DrawModel], limit: int = 3000) -> list[DrawModel]:
    return [
        draw
        for draw in history
        if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
    ][-limit:]


def _normalize(values: list[float]) -> list[float]:
    safe = [
        float(value) if math.isfinite(float(value)) and float(value) > 0 else 1e-12
        for value in values
    ]
    total = sum(safe) or 1.0
    return [value / total for value in safe]


def _bounded_weights(
    values: Mapping[str, float],
    floor: float = 0.02,
    cap: float = 0.45,
) -> dict[str, float]:
    names = tuple(values)
    if not names:
        return {}
    safe = {name: max(1e-12, float(values[name])) for name in names}
    for _ in range(10):
        total = sum(safe.values()) or 1.0
        safe = {name: value / total for name, value in safe.items()}
        fixed = {
            name: floor if value < floor else cap
            for name, value in safe.items()
            if value < floor or value > cap
        }
        if not fixed:
            break
        free = [name for name in names if name not in fixed]
        remaining = max(0.0, 1.0 - sum(fixed.values()))
        free_total = sum(safe[name] for name in free) or 1.0
        safe = {
            name: fixed.get(name, remaining * safe[name] / free_total)
            for name in names
        }
    total = sum(safe.values()) or 1.0
    return {name: value / total for name, value in safe.items()}


def _group_component(
    values: list[int],
    groups: Mapping[int, tuple[int, ...]],
) -> list[float]:
    number_to_group = {
        number: group
        for group, numbers in groups.items()
        for number in numbers
    }
    windows = ((18, 0.50), (45, 0.30), (120, 0.20))
    group_scores = {group: 0.0 for group in groups}
    for window, mix in windows:
        subset = values[-min(window, len(values)):]
        denominator = float(len(subset) + len(groups))
        for group in groups:
            count = sum(number_to_group.get(number) == group for number in subset)
            group_scores[group] += mix * (count + 1.0) / denominator

    long_values = values[-min(120, len(values)):]
    long_counts = {number: long_values.count(number) for number in range(1, 11)}
    raw: list[float] = []
    for number in range(1, 11):
        group = number_to_group[number]
        members = groups[group]
        within_total = sum(long_counts[item] + 1.0 for item in members)
        within = (long_counts[number] + 1.0) / within_total
        raw.append(group_scores[group] * within)
    return _normalize(raw)


def _universal_pool_component(values: list[int]) -> list[float]:
    current = values[-1]
    pool = set(UNIVERSAL_POOLS[current])
    successors = [0.0] * 10
    matching = 0
    for index in range(1, len(values)):
        if values[index - 1] == current:
            successors[values[index] - 1] += 1.0
            matching += 1

    recent_transitions = list(zip(values[-121:-1], values[-120:]))
    if not recent_transitions:
        recent_transitions = list(zip(values[:-1], values[1:]))
    pool_hits = [
        int(next_value in UNIVERSAL_POOLS[previous])
        for previous, next_value in recent_transitions
    ]
    reliability = (sum(pool_hits) + 6.0) / (len(pool_hits) + 10.0)
    membership_boost = max(0.78, min(1.35, 1.0 + (reliability - 0.60) * 1.5))
    shrink = max(10.0, 28.0 - matching)
    long_counts = [values[-120:].count(number) + 1.0 for number in range(1, 11)]
    long_total = sum(long_counts)
    raw = []
    for index, number in enumerate(range(1, 11)):
        transition = successors[index] + shrink * long_counts[index] / long_total
        structure = (
            membership_boost
            if number in pool
            else max(0.45, 1.15 - membership_boost)
        )
        raw.append(transition * structure)
    return _normalize(raw)


def continual_strategy_components(
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

    base = strategy_components(verified, position)
    values = [draw.numbers[position] for draw in verified]
    base.update(
        {
            "route012": _group_component(
                values,
                {
                    0: (3, 6, 9),
                    1: (1, 4, 7, 10),
                    2: (2, 5, 8),
                },
            ),
            "parity_structure": _group_component(
                values,
                {
                    0: (2, 4, 6, 8, 10),
                    1: (1, 3, 5, 7, 9),
                },
            ),
            "size_structure": _group_component(
                values,
                {
                    0: (1, 2, 3, 4, 5),
                    1: (6, 7, 8, 9, 10),
                },
            ),
            "universal_pool": _universal_pool_component(values),
        }
    )
    return base


def learn_position_weights(
    history: list[DrawModel],
    position: int,
    *,
    fallback: Mapping[str, float] | None = None,
    max_samples: int = 72,
) -> dict[str, float]:
    verified = _canonical(history)
    current_components = continual_strategy_components(verified, position)
    prior = normalize_strategy_weights(fallback, current_components)
    if len(verified) < 42:
        return prior

    start = max(30, len(verified) - max(24, max_samples))
    events: dict[str, list[dict[str, float | bool]]] = {
        name: [] for name in current_components
    }
    for cursor in range(start, len(verified)):
        prefix = verified[:cursor]
        components = continual_strategy_components(prefix, position)
        actual = verified[cursor].numbers[position]
        for name, probabilities in components.items():
            events[name].append(prediction_loss(probabilities, actual))

    raw_scores: dict[str, float] = {}
    windows = ((24, 0.50), (48, 0.30), (None, 0.20))
    for name, rows in events.items():
        evidence = 0.0
        for limit, mix in windows:
            subset = rows if limit is None else rows[-limit:]
            if not subset:
                continue
            mean_loss = sum(float(item["combined_loss"]) for item in subset) / len(subset)
            hit_rate = sum(bool(item["top6_hit"]) for item in subset) / len(subset)
            target = max_samples if limit is None else limit
            reliability = min(1.0, len(subset) / float(max(1, target)))
            loss_edge = max(-0.9, min(0.9, UNIFORM_LOG_LOSS - mean_loss))
            hit_edge = max(-0.3, min(0.3, hit_rate - 0.60))
            evidence += mix * reliability * (loss_edge + 0.8 * hit_edge)
        raw_scores[name] = (
            max(1e-12, prior.get(name, 1e-12)) * math.exp(evidence)
        )
    return _bounded_weights(raw_scores)


def build_position_profile(
    history: list[DrawModel],
    position: int,
    *,
    fallback_weights: Mapping[str, float] | None = None,
    max_validation_samples: int = 60,
) -> ContinualPositionProfile:
    verified = _canonical(history)
    if len(verified) < 30:
        raise ValueError("至少需要30期有效历史")

    current_weights = learn_position_weights(
        verified,
        position,
        fallback=fallback_weights,
    )
    current_components = continual_strategy_components(verified, position)
    current = blend_strategy_probabilities(current_components, current_weights)
    ranked = sorted(range(10), key=current.__getitem__, reverse=True)
    boundary = current[ranked[5]] - current[ranked[6]]

    if len(verified) < 48:
        return ContinualPositionProfile(
            position=position,
            probabilities=current,
            top6=[index + 1 for index in ranked[:6]],
            top7=[index + 1 for index in ranked[:7]],
            boundary_margin=boundary,
            walk_forward_samples=0,
            walk_forward_hits=0,
            walk_forward_hit_rate=0.60,
            average_log_loss=UNIFORM_LOG_LOSS,
            validation_score=1.0 + boundary * 3.0,
            excess_hit_rate=0.0,
            max_miss_streak=0,
            strategy_probabilities=current_components,
            strategy_weights=current_weights,
        )

    validation_count = min(
        max_validation_samples,
        max(12, len(verified) - 36),
    )
    validation_start = len(verified) - validation_count
    training = verified[:validation_start]
    validation_weights = learn_position_weights(
        training,
        position,
        fallback=fallback_weights,
        max_samples=min(72, max(24, len(training) - 30)),
    )

    hits = 0
    losses: list[float] = []
    current_miss = 0
    max_miss = 0
    half_hits = [0, 0]
    half_samples = [0, 0]
    midpoint = validation_start + validation_count // 2
    for cursor in range(validation_start, len(verified)):
        prefix = verified[:cursor]
        components = continual_strategy_components(prefix, position)
        probabilities = blend_strategy_probabilities(components, validation_weights)
        actual = verified[cursor].numbers[position]
        metric = prediction_loss(probabilities, actual)
        hit = bool(metric["top6_hit"])
        hits += int(hit)
        losses.append(float(metric["log_loss"]))
        bucket = 0 if cursor < midpoint else 1
        half_hits[bucket] += int(hit)
        half_samples[bucket] += 1
        if hit:
            current_miss = 0
        else:
            current_miss += 1
            max_miss = max(max_miss, current_miss)

    samples = validation_count
    posterior_hit_rate = (hits + 6.0) / (samples + 10.0)
    average_log_loss = sum(losses) / len(losses) if losses else UNIFORM_LOG_LOSS
    loss_edge = max(
        -0.35,
        min(0.35, (UNIFORM_LOG_LOSS - average_log_loss) / UNIFORM_LOG_LOSS),
    )
    excess_hit_rate = posterior_hit_rate - 0.60
    first_rate = half_hits[0] / half_samples[0] if half_samples[0] else 0.60
    second_rate = half_hits[1] / half_samples[1] if half_samples[1] else 0.60
    stability = max(0.0, 1.0 - abs(first_rate - second_rate))
    reliability = min(1.0, samples / 60.0)
    streak_penalty = max(0, max_miss - 3) * 0.045
    validation_score = max(
        0.05,
        1.0
        + reliability * (excess_hit_rate * 5.2 + loss_edge * 1.4)
        + boundary * 3.0
        + stability * 0.12
        - streak_penalty,
    )
    return ContinualPositionProfile(
        position=position,
        probabilities=current,
        top6=[index + 1 for index in ranked[:6]],
        top7=[index + 1 for index in ranked[:7]],
        boundary_margin=boundary,
        walk_forward_samples=samples,
        walk_forward_hits=hits,
        walk_forward_hit_rate=posterior_hit_rate,
        average_log_loss=average_log_loss,
        validation_score=validation_score,
        excess_hit_rate=excess_hit_rate,
        max_miss_streak=max_miss,
        strategy_probabilities=current_components,
        strategy_weights=current_weights,
    )


def regularize_continual_recent_copy(
    probabilities: list[float],
    history: list[DrawModel],
    position: int,
    *,
    strategy_weights: Mapping[str, float],
    mask_recent: int = 10,
) -> tuple[list[float], bool]:
    verified = _canonical(history)
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
    recent_six = {draw.numbers[position] for draw in verified[-6:]}
    recent_seven = {draw.numbers[position] for draw in verified[-7:]}
    top6 = {index + 1 for index in ranked[:6]}
    top7 = {index + 1 for index in ranked[:7]}
    triggered = (
        (len(recent_six) == 6 and top6 == recent_six)
        or (len(recent_six) >= 5 and len(top6 & recent_six) >= 5)
        or (len(recent_seven) >= 6 and recent_seven.issubset(top7))
    )
    if not triggered:
        return _normalize(probabilities), False

    safe_mask = min(mask_recent, max(0, len(verified) - 30))
    adjusted = list(probabilities)
    if safe_mask > 0:
        masked_components = continual_strategy_components(
            verified,
            position,
            mask_recent=safe_mask,
        )
        masked = blend_strategy_probabilities(masked_components, strategy_weights)
        adjusted = _normalize(
            [
                adjusted[index] * 0.32 + masked[index] * 0.68
                for index in range(10)
            ]
        )
    adjusted = _normalize(
        [
            value * (0.80 if index + 1 in recent_six else 1.20)
            for index, value in enumerate(adjusted)
        ]
    )
    return adjusted, True
