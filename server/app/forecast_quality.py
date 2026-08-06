from __future__ import annotations

from dataclasses import dataclass
import math

from .models import DrawModel


@dataclass(frozen=True)
class PositionQuality:
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


@dataclass(frozen=True)
class RecentCopyDiagnostics:
    triggered: bool
    exact_latest_six: bool
    recent_six_unique: int
    top6_recent_six_overlap: int
    recent_seven_unique: int
    top7_contains_recent_seven: bool


def _normalize(values: list[float]) -> list[float]:
    safe = [value if math.isfinite(value) and value > 0 else 1e-12 for value in values]
    total = sum(safe) or 1.0
    return [value / total for value in safe]


def _canonical(history: list[DrawModel], limit: int = 240) -> list[DrawModel]:
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


def statistical_probabilities(
    history: list[DrawModel],
    position: int,
    *,
    mask_recent: int = 0,
) -> list[float]:
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

    long_prior = _normalize([(value + 1.0) / (size120 + 10.0) for value in count120])

    recency_raw = [0.0] * 10
    for index, number in enumerate(values):
        age = len(values) - 1 - index
        recency_raw[number - 1] += math.exp(-age / 24.0)
    recency = _normalize(recency_raw)

    omission_raw: list[float] = []
    for number in range(1, 11):
        latest = -1
        for cursor in range(len(values) - 1, -1, -1):
            if values[cursor] == number:
                latest = cursor
                break
        gap = len(values) if latest < 0 else len(values) - 1 - latest
        omission_raw.append(0.72 + math.exp(-abs(gap - 9.0) / 9.0))
    omission = _normalize(omission_raw)

    current = values[-1]
    successors = [0.0] * 10
    transition_samples = 0
    for index in range(1, len(values)):
        if values[index - 1] == current:
            successors[values[index] - 1] += 1.0
            transition_samples += 1
    transition_shrink = max(7.0, 22.0 - transition_samples)
    transition = _normalize(
        [successors[index] + long_prior[index] * transition_shrink for index in range(10)]
    )

    trend = _normalize(
        [
            math.exp(
                (count18[index] / size18 - count45[index] / size45) * 4.2
            )
            for index in range(10)
        ]
    )
    stability = _normalize(
        [
            1.0
            / (
                0.08
                + abs(count18[index] / size18 - count45[index] / size45)
                + 0.45 * abs(count45[index] / size45 - count120[index] / size120)
            )
            for index in range(10)
        ]
    )

    # Recency is deliberately capped. It may contribute evidence, but cannot by itself
    # turn the most recent distinct values into the entire Top 6.
    weights = (0.25, 0.15, 0.12, 0.23, 0.16, 0.09)
    factors = (long_prior, recency, omission, transition, trend, stability)
    return _normalize(
        [
            sum(factors[factor][number] * weights[factor] for factor in range(6))
            for number in range(10)
        ]
    )


def blend_probabilities(
    primary: list[float],
    secondary: list[float],
    *,
    secondary_weight: float,
) -> list[float]:
    weight = max(0.0, min(1.0, secondary_weight))
    return _normalize(
        [
            primary[index] * (1.0 - weight) + secondary[index] * weight
            for index in range(len(primary))
        ]
    )


def position_quality_profile(
    history: list[DrawModel],
    position: int,
    *,
    max_samples: int = 48,
) -> PositionQuality:
    verified = _canonical(history)
    if len(verified) < 40:
        probabilities = statistical_probabilities(verified, position)
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
        return PositionQuality(
            position=position,
            probabilities=probabilities,
            top6=[index + 1 for index in ranked[:6]],
            top7=[index + 1 for index in ranked[:7]],
            boundary_margin=probabilities[ranked[5]] - probabilities[ranked[6]],
            walk_forward_samples=0,
            walk_forward_hits=0,
            walk_forward_hit_rate=0.6,
            average_log_loss=math.log(10.0),
            validation_score=1.0,
        )

    start = max(30, len(verified) - max(12, max_samples))
    hits = 0
    losses: list[float] = []
    samples = 0
    for cursor in range(start, len(verified)):
        prefix = verified[:cursor]
        if len(prefix) < 30:
            continue
        probabilities = statistical_probabilities(prefix, position)
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
        actual = verified[cursor].numbers[position]
        if actual in {index + 1 for index in ranked[:6]}:
            hits += 1
        losses.append(-math.log(max(1e-12, probabilities[actual - 1])))
        samples += 1

    current = statistical_probabilities(verified, position)
    ranked = sorted(range(10), key=current.__getitem__, reverse=True)
    boundary = current[ranked[5]] - current[ranked[6]]
    posterior_hit_rate = (hits + 6.0) / (samples + 10.0)
    average_log_loss = sum(losses) / len(losses) if losses else math.log(10.0)
    baseline_loss = math.log(10.0)
    loss_edge = max(-0.35, min(0.35, (baseline_loss - average_log_loss) / baseline_loss))
    validation_score = max(
        0.05,
        1.0
        + (posterior_hit_rate - 0.6) * 5.0
        + loss_edge * 0.9
        + boundary * 4.0,
    )
    return PositionQuality(
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
    )


def recent_copy_diagnostics(
    ranked: list[int],
    history: list[DrawModel],
    position: int,
) -> RecentCopyDiagnostics:
    verified = _canonical(history)
    top6 = {index + 1 for index in ranked[:6]}
    top7 = {index + 1 for index in ranked[:7]}
    recent_six = {draw.numbers[position] for draw in verified[-6:]}
    recent_seven = {draw.numbers[position] for draw in verified[-7:]}
    overlap = len(top6 & recent_six)
    exact = len(recent_six) == 6 and top6 == recent_six
    contains_seven = len(recent_seven) >= 6 and recent_seven.issubset(top7)
    triggered = exact or (len(recent_six) >= 5 and overlap >= 5) or contains_seven
    return RecentCopyDiagnostics(
        triggered=triggered,
        exact_latest_six=exact,
        recent_six_unique=len(recent_six),
        top6_recent_six_overlap=overlap,
        recent_seven_unique=len(recent_seven),
        top7_contains_recent_seven=contains_seven,
    )


def regularize_recent_copy(
    probabilities: list[float],
    history: list[DrawModel],
    position: int,
    *,
    mask_recent: int = 10,
) -> tuple[list[float], bool]:
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
    diagnostics = recent_copy_diagnostics(ranked, history, position)
    if not diagnostics.triggered:
        return _normalize(probabilities), False

    verified = _canonical(history)
    safe_mask = min(mask_recent, max(0, len(verified) - 30))
    adjusted = list(probabilities)
    if safe_mask > 0:
        masked = statistical_probabilities(verified, position, mask_recent=safe_mask)
        adjusted = blend_probabilities(adjusted, masked, secondary_weight=0.68)

    recent_six = {draw.numbers[position] for draw in verified[-6:]}
    adjusted = _normalize(
        [
            value * (0.78 if index + 1 in recent_six else 1.22)
            for index, value in enumerate(adjusted)
        ]
    )

    # Final deterministic guard: an exact clone of six latest distinct values is not
    # accepted when the sixth/seventh boundary is weak. Replace only the weakest edge.
    reranked = sorted(range(10), key=adjusted.__getitem__, reverse=True)
    reranked_top6 = {index + 1 for index in reranked[:6]}
    if len(recent_six) == 6 and reranked_top6 == recent_six:
        inside = min(reranked[:6], key=adjusted.__getitem__)
        outside = max(reranked[6:], key=adjusted.__getitem__)
        boundary = adjusted[inside] - adjusted[outside]
        if boundary < 0.025:
            pivot = (adjusted[inside] + adjusted[outside]) / 2.0
            adjusted[inside] = max(1e-12, pivot * 0.995)
            adjusted[outside] = pivot * 1.005
            adjusted = _normalize(adjusted)
    return adjusted, True
