from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

from . import ai_ensemble


TARGET_NUMBERS: tuple[int, ...] = (2, 3, 5, 7, 8, 10)
TARGET_LABEL = "235780"
RANDOM_BASELINE = 0.60
BINARY_LOG_LOSS_BASELINE = -(
    RANDOM_BASELINE * math.log(RANDOM_BASELINE)
    + (1.0 - RANDOM_BASELINE) * math.log(1.0 - RANDOM_BASELINE)
)

_INSTALLED = False
_PREVIOUS_ANALYZE = ai_ensemble.analyze_ensemble


@dataclass(frozen=True)
class FixedTargetPositionProfile:
    position: int
    target_probability: float
    exact_probabilities: list[float]
    validation_samples: int
    validation_hits: int
    validation_hit_rate: float
    average_log_loss: float
    average_brier: float
    max_miss_streak: int
    current_miss_streak: int
    score: float

    @property
    def excess_over_random(self) -> float:
        return self.validation_hit_rate - RANDOM_BASELINE


def _canonical(history: list[Any], limit: int = 240) -> list[Any]:
    return [
        draw
        for draw in history
        if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
    ][-limit:]


def _is_target(number: int) -> bool:
    return int(number) in TARGET_NUMBERS


def _beta_rate(hits: float, total: float, prior_strength: float = 10.0) -> float:
    return (hits + RANDOM_BASELINE * prior_strength) / (total + prior_strength)


def _fixed_target_probability(values: list[int]) -> float:
    if not values:
        return RANDOM_BASELINE

    windows = ((12, 0.36), (30, 0.30), (60, 0.22), (120, 0.12))
    multiscale = 0.0
    for window, weight in windows:
        subset = values[-min(window, len(values)):]
        hits = sum(_is_target(value) for value in subset)
        multiscale += weight * _beta_rate(hits, len(subset))

    decay_weight = 1.0
    decay_hits = 0.0
    decay_total = 0.0
    for value in reversed(values[-120:]):
        decay_total += decay_weight
        if _is_target(value):
            decay_hits += decay_weight
        decay_weight *= 0.94
    recency = _beta_rate(decay_hits, decay_total, prior_strength=5.0)

    current_state = _is_target(values[-1])
    transition_hits = 0
    transition_total = 0
    for index in range(1, len(values)):
        if _is_target(values[index - 1]) == current_state:
            transition_total += 1
            transition_hits += int(_is_target(values[index]))
    transition = _beta_rate(transition_hits, transition_total, prior_strength=8.0)

    current_number = values[-1]
    successor_hits = 0
    successor_total = 0
    for index in range(1, len(values)):
        if values[index - 1] == current_number:
            successor_total += 1
            successor_hits += int(_is_target(values[index]))
    successor = _beta_rate(successor_hits, successor_total, prior_strength=7.0)

    probability = (
        multiscale * 0.46
        + recency * 0.24
        + transition * 0.20
        + successor * 0.10
    )
    reliability = min(1.0, len(values) / 120.0)
    probability = RANDOM_BASELINE + (probability - RANDOM_BASELINE) * (0.45 + 0.55 * reliability)
    return max(0.38, min(0.82, probability))


def _group_distribution(values: list[int], target_probability: float) -> list[float]:
    recent = values[-min(60, len(values)):]
    counts = {number: recent.count(number) + 1.5 for number in range(1, 11)}
    target_total = sum(counts[number] for number in TARGET_NUMBERS)
    outside = tuple(number for number in range(1, 11) if number not in TARGET_NUMBERS)
    outside_total = sum(counts[number] for number in outside)
    result: list[float] = []
    for number in range(1, 11):
        if number in TARGET_NUMBERS:
            result.append(target_probability * counts[number] / target_total)
        else:
            result.append((1.0 - target_probability) * counts[number] / outside_total)
    total = sum(result) or 1.0
    return [value / total for value in result]


def _current_miss_streak(values: list[int]) -> int:
    streak = 0
    for value in reversed(values):
        if _is_target(value):
            break
        streak += 1
    return streak


def _build_position_profile(
    history: list[Any],
    position: int,
    *,
    max_validation_samples: int = 60,
) -> FixedTargetPositionProfile:
    verified = _canonical(history)
    if len(verified) < 30:
        raise ValueError("固定六码235780预测至少需要30期有效历史")
    values = [draw.numbers[position] for draw in verified]
    current_probability = _fixed_target_probability(values)
    exact_probabilities = _group_distribution(values, current_probability)

    start = max(30, len(verified) - max(24, max_validation_samples))
    hits = 0
    samples = 0
    losses: list[float] = []
    briers: list[float] = []
    running_miss = 0
    max_miss = 0
    for cursor in range(start, len(verified)):
        prefix_values = [draw.numbers[position] for draw in verified[:cursor]]
        probability = _fixed_target_probability(prefix_values)
        actual_hit = _is_target(verified[cursor].numbers[position])
        outcome = 1.0 if actual_hit else 0.0
        hits += int(actual_hit)
        samples += 1
        losses.append(-math.log(max(1e-12, probability if actual_hit else 1.0 - probability)))
        briers.append((probability - outcome) ** 2)
        if actual_hit:
            running_miss = 0
        else:
            running_miss += 1
            max_miss = max(max_miss, running_miss)

    hit_rate = (hits + 6.0) / (samples + 10.0) if samples else RANDOM_BASELINE
    average_log_loss = sum(losses) / len(losses) if losses else BINARY_LOG_LOSS_BASELINE
    average_brier = sum(briers) / len(briers) if briers else RANDOM_BASELINE * (1.0 - RANDOM_BASELINE)
    reliability = min(1.0, samples / 60.0)
    loss_edge = max(
        -0.35,
        min(
            0.35,
            (BINARY_LOG_LOSS_BASELINE - average_log_loss) / BINARY_LOG_LOSS_BASELINE,
        ),
    )
    hit_edge = max(-0.25, min(0.25, hit_rate - RANDOM_BASELINE))
    current_edge = current_probability - RANDOM_BASELINE
    streak_penalty = max(0, max_miss - 4) * 0.015
    score = (
        current_probability
        + reliability * hit_edge * 0.24
        + reliability * loss_edge * 0.08
        - streak_penalty
    )
    return FixedTargetPositionProfile(
        position=position,
        target_probability=current_probability,
        exact_probabilities=exact_probabilities,
        validation_samples=samples,
        validation_hits=hits,
        validation_hit_rate=hit_rate,
        average_log_loss=average_log_loss,
        average_brier=average_brier,
        max_miss_streak=max_miss,
        current_miss_streak=_current_miss_streak(values),
        score=score + current_edge * 0.35,
    )


def build_fixed_target_profiles(history: list[Any]) -> tuple[FixedTargetPositionProfile, ...]:
    return tuple(_build_position_profile(history, position) for position in range(10))


def _top7(probabilities: list[float]) -> list[int]:
    outside = [number for number in range(1, 11) if number not in TARGET_NUMBERS]
    hedge = max(outside, key=lambda number: probabilities[number - 1])
    return [*TARGET_NUMBERS, hedge]


def _analyze_fixed_target(
    history: list[Any],
    target_period: str,
    config: Any,
    *,
    recent_positions: list[int] | None = None,
    strategy_weights: dict[str, float] | None = None,
) -> Any:
    # Keep the configured language model call as an independent audit signal, but do not allow
    # its old generic number-ranking objective to change the fixed 235780 target definition.
    remote = _PREVIOUS_ANALYZE(
        history,
        target_period,
        config,
        recent_positions=recent_positions,
        strategy_weights=strategy_weights,
    )
    profiles = build_fixed_target_profiles(history)
    selected = max(profiles, key=lambda profile: profile.score)
    probabilities = selected.exact_probabilities
    ranked_profiles = sorted(profiles, key=lambda profile: profile.score, reverse=True)
    runner_up = ranked_profiles[1]
    edge = selected.target_probability - RANDOM_BASELINE
    gap = selected.target_probability - runner_up.target_probability
    remote_agreement = int(remote.position) == selected.position
    analysis = (
        f"预测目标已固定为六码{TARGET_LABEL}（0按10处理，内部集合2/3/5/7/8/10），不再预测动态六码。"
        f"十个名次分别做二分类持续学习；第{selected.position + 1}名下一期落入固定六码的模型概率约"
        f"{selected.target_probability * 100:.1f}%，相对60%随机基准{edge * 100:+.1f}个百分点，"
        f"领先第二候选约{gap * 100:+.1f}个百分点。滚动验证{selected.validation_samples}期，"
        f"固定六码命中率约{selected.validation_hit_rate * 100:.1f}%，最长连续未进固定六码"
        f"{selected.max_miss_streak}期，当前连续未进{selected.current_miss_streak}期。"
        + (
            " 独立语言模型原始历史评审与固定目标模型选择同一名次。"
            if remote_agreement
            else f" 独立语言模型旧通用评审选择第{int(remote.position) + 1}名，仅作旁路审计，不覆盖固定目标决策。"
        )
    )[:1200]
    risk_note = (
        f"{remote.risk_note} 当前任务仅判断某名次是否落入固定六码{TARGET_LABEL}；"
        "每期开奖恰有6个位置属于该集合，因此任取一个位置的随机命中基准是60%。"
        "模型只能用前向历史寻找相对偏离，不能把短期偏离当成稳定规律。"
    )[:800]
    strategy_name = f"ai_fixed_{TARGET_LABEL}_position_{selected.position + 1}"
    return replace(
        remote,
        position=selected.position,
        probabilities=probabilities,
        top6=list(TARGET_NUMBERS),
        top7=_top7(probabilities),
        analysis=analysis,
        risk_note=risk_note,
        strategy_probabilities={strategy_name: probabilities},
        strategy_weights={strategy_name: 1.0},
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ai_ensemble.analyze_ensemble = _analyze_fixed_target
    _INSTALLED = True
