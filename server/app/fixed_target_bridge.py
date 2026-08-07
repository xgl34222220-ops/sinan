from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any

from . import ai_ensemble


TARGET_NUMBERS: tuple[int, ...] = (2, 3, 5, 7, 8, 10)
TARGET_LABEL = "235780"
RANDOM_BASELINE = 0.60
TARGET_REVIEWERS = 3
BINARY_LOG_LOSS_BASELINE = -(
    RANDOM_BASELINE * math.log(RANDOM_BASELINE)
    + (1.0 - RANDOM_BASELINE) * math.log(1.0 - RANDOM_BASELINE)
)

_INSTALLED = False


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


def _normalize(values: list[float]) -> list[float]:
    safe = [value if math.isfinite(value) and value > 0 else 1e-12 for value in values]
    total = sum(safe) or 1.0
    return [value / total for value in safe]


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
    return _normalize(result)


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
        + current_edge * 0.35
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
        score=score,
    )


def build_fixed_target_profiles(history: list[Any]) -> tuple[FixedTargetPositionProfile, ...]:
    return tuple(_build_position_profile(history, position) for position in range(10))


def _target_membership_history(
    history: list[Any],
    neutral_mapping: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        {
            "period": draw.period,
            "target_hit_by_candidate": {
                neutral_id: int(_is_target(draw.numbers[position]))
                for neutral_id, position in neutral_mapping.items()
            },
        }
        for draw in _canonical(history, 120)
    ]


def _profile_evidence(profile: FixedTargetPositionProfile) -> dict[str, Any]:
    return {
        "position": profile.position + 1,
        "current_target_probability": round(profile.target_probability, 6),
        "validation_samples": profile.validation_samples,
        "validation_hits": profile.validation_hits,
        "validation_hit_rate": round(profile.validation_hit_rate, 6),
        "excess_over_random_60pct": round(profile.excess_over_random, 6),
        "average_binary_log_loss": round(profile.average_log_loss, 6),
        "average_brier": round(profile.average_brier, 6),
        "longest_miss_streak": profile.max_miss_streak,
        "current_miss_streak": profile.current_miss_streak,
    }


def _target_position_review(
    config: Any,
    *,
    history: list[Any],
    profiles: tuple[FixedTargetPositionProfile, ...],
    target_period: str,
    reviewer: int,
) -> Any:
    evidence = [_profile_evidence(profile) for profile in profiles]
    shared_candidates, neutral_mapping, neutral_by_actual = ai_ensemble._shared_anonymized_items(
        evidence,
        target_period=target_period,
        phase="fixed-235780-shared",
    )
    _, reviewer_mapping = ai_ensemble._anonymized_items(
        evidence,
        target_period=target_period,
        phase="fixed-235780-review",
        reviewer=reviewer,
    )
    trained_through = _canonical(history, 120)[-1].period
    prompt = (
        "你是天机的固定目标名次评审。唯一任务：预测下一期十个匿名位置中，哪个位置的号码最可能属于固定集合"
        "2/3/5/7/8/10（界面写作235780，其中0代表10）。禁止生成、替换或优化这组六码。"
        "每个位置在随机排列下命中该集合的基准是60%，所以短期命中率高于60%本身不构成强证据。"
        "你会看到每个匿名位置的完整0/1命中序列，以及严格前向验证得到的命中率、相对60%超额、"
        "二分类LogLoss、Brier和连续未中。请比较十个候选，优先可信的前向证据并对小样本和短期波动降权。"
        "只返回紧凑JSON：{\"scores\":{\"A\":数值,...,\"J\":数值},"
        "\"selected\":\"A至J之一\",\"analysis\":\"不超过120字简体中文\"}。"
    )
    result = ai_ensemble._call_json(
        config,
        system_prompt=prompt,
        shared_payload={
            "target_period": target_period,
            "trained_through_period": trained_through,
            "fixed_target": TARGET_LABEL,
            "internal_target_numbers": list(TARGET_NUMBERS),
            "random_position_baseline": RANDOM_BASELINE,
            "history_order": "oldest_to_newest",
            "neutral_target_membership_history": _target_membership_history(history, neutral_mapping),
            "neutral_candidates": shared_candidates,
        },
        reviewer_payload={
            "reviewer": reviewer + 1,
            "independent_review": True,
            "candidate_aliases_A_to_J": ai_ensemble._reviewer_aliases(
                reviewer_mapping,
                neutral_by_actual,
            ),
            "review_instruction": "只评价下一期进入固定235780集合的相对可能性，不评价具体号码排序。",
        },
        max_tokens=900,
        timeout_seconds=45,
    )
    return ai_ensemble._parse_label_scores(result, reviewer_mapping)


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
    del strategy_weights
    started = time.monotonic()
    profiles = build_fixed_target_profiles(history)
    reviews = ai_ensemble._run_prefix_cached(
        TARGET_REVIEWERS,
        lambda reviewer: _target_position_review(
            config,
            history=history,
            profiles=profiles,
            target_period=target_period,
            reviewer=reviewer,
        ),
    )
    ai_scores = _normalize([
        sum(review.scores[position] for review in reviews) / len(reviews)
        for position in range(10)
    ])
    math_scores = _normalize([max(1e-9, profile.score) for profile in profiles])
    combined_scores = [
        math_scores[position] * 0.68 + ai_scores[position] * 0.32
        for position in range(10)
    ]
    if recent_positions and len(recent_positions) >= 3:
        repeated = recent_positions[-1]
        if all(position == repeated for position in recent_positions[-3:]) and repeated in range(10):
            combined_scores[repeated] *= 0.985
    selected_index = max(range(10), key=lambda position: combined_scores[position])
    selected = profiles[selected_index]
    probabilities = selected.exact_probabilities
    ranked_positions = sorted(range(10), key=lambda position: combined_scores[position], reverse=True)
    runner_up = profiles[ranked_positions[1]]
    edge = selected.target_probability - RANDOM_BASELINE
    gap = selected.target_probability - runner_up.target_probability
    ai_best = max(range(10), key=lambda position: ai_scores[position])
    ai_support = sum(
        max(range(10), key=lambda position: review.scores[position]) == selected.position
        for review in reviews
    )
    analyses = "；".join(review.analysis for review in reviews if review.analysis)[:300]
    analysis = (
        f"固定目标六码{TARGET_LABEL}（0按10处理，内部集合2/3/5/7/8/10）。"
        f"十个名次先做严格二分类前向验证，再由{len(reviews)}路AI直接针对‘下一期是否进入235780’独立复核；"
        f"数学证据权重68%，AI固定目标评审权重32%。最终第{selected.position + 1}名最高，"
        f"模型目标概率约{selected.target_probability * 100:.1f}%，相对60%随机基准{edge * 100:+.1f}个百分点，"
        f"与第二候选概率差约{gap * 100:+.1f}个百分点。滚动验证{selected.validation_samples}期，"
        f"命中率约{selected.validation_hit_rate * 100:.1f}%，最长连续未进{selected.max_miss_streak}期，"
        f"当前连续未进{selected.current_miss_streak}期。AI平均首选第{ai_best + 1}名，"
        f"{ai_support}/{len(reviews)}路AI直接支持最终名次。"
        + (f" AI摘要：{analyses}" if analyses else "")
    )[:1200]
    risk_note = (
        f"本任务固定目标只有{TARGET_LABEL}，不会动态换码。每期开奖恰有6个位置属于该集合，"
        "因此任取一个位置的随机命中基准就是60%；只有持续的前向超额和更好的概率损失才算有效证据，"
        "短期偏离不能视为可保证规律。"
    )[:800]
    usage = ai_ensemble._merge_usage(reviews)
    prompt_total = usage.get("prompt_cache_hit_tokens", 0) + usage.get("prompt_cache_miss_tokens", 0)
    cache_hit_rate = (
        usage.get("prompt_cache_hit_tokens", 0) / prompt_total
        if prompt_total > 0
        else 0.0
    )
    strategy_name = f"ai_fixed_{TARGET_LABEL}_position_{selected.position + 1}"
    return ai_ensemble.AiEnsembleResult(
        position=selected.position,
        probabilities=probabilities,
        top6=list(TARGET_NUMBERS),
        top7=_top7(probabilities),
        analysis=analysis,
        risk_note=risk_note,
        latency_ms=int((time.monotonic() - started) * 1000),
        position_reviewers=len(reviews),
        number_reviewers=0,
        collapse_reviewed=False,
        recent_copy_reviewed=False,
        request_count=usage.get("request_count", 0),
        prompt_tokens=usage.get("prompt_tokens", 0),
        prompt_cache_hit_tokens=usage.get("prompt_cache_hit_tokens", 0),
        prompt_cache_miss_tokens=usage.get("prompt_cache_miss_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        reasoning_tokens=usage.get("reasoning_tokens", 0),
        cache_hit_rate=cache_hit_rate,
        strategy_probabilities={strategy_name: probabilities},
        strategy_weights={strategy_name: 1.0},
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ai_ensemble.analyze_ensemble = _analyze_fixed_target
    _INSTALLED = True
