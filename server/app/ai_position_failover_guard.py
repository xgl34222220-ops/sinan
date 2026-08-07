from __future__ import annotations

import time
from typing import Any, Iterable

from . import ai_ensemble, fixed_target_bridge, fixed_target_runtime_guard
from .db import database


MATH_WEIGHT = 0.80
AI_WEIGHT = 0.20
_FIXED = tuple(fixed_target_bridge.TARGET_NUMBERS)
_INSTALLED = False


def _leading_same_position_misses(
    forecasts: Iterable[Any],
    *,
    model: str,
) -> tuple[int | None, int]:
    """Return the latest consecutive failed recommendations for one AI position.

    This is feedback about Tianji's *recommendation quality*, not a claim that a
    lottery position is "due" after missing. A hit, a model switch, or a change
    to another recommended position ends the streak.
    """
    failed_position: int | None = None
    count = 0
    for forecast in forecasts:
        if str(getattr(forecast, "source", "")) != "ai":
            continue
        if str(getattr(forecast, "model", "")) != model:
            continue
        hit = getattr(forecast, "top6_hit", None)
        actual = getattr(forecast, "actual_number", None)
        if hit is None or actual is None:
            continue
        if bool(hit):
            break
        position = int(getattr(forecast, "position"))
        if failed_position is None:
            failed_position = position
        elif position != failed_position:
            break
        count += 1
    return failed_position, count


def _recent_failed_position_streak(history: list[Any], model: str) -> tuple[int | None, int]:
    if not history:
        return None, 0
    lottery = str(getattr(history[-1], "lottery", ""))
    if not lottery:
        return None, 0
    recent = database.list_forecasts(lottery, 30)
    return _leading_same_position_misses(recent, model=model)


def _review_support(reviews: list[Any], position: int) -> int:
    support = 0
    for review in reviews:
        scores = list(getattr(review, "scores", []) or [])
        if len(scores) != 10:
            continue
        if max(range(10), key=lambda index: scores[index]) == position:
            support += 1
    return support


def _apply_failover(
    combined: list[float],
    reviews: list[Any],
    *,
    failed_position: int | None,
    miss_count: int,
) -> tuple[list[float], int, str]:
    """Penalize a repeatedly failing *recommendation* without gambler's fallacy.

    - <2 consecutive misses: no intervention.
    - 2 misses on the same recommended position: AI reviewer support decides how
      strongly to reduce that position's selection score.
    - >=3 misses on the same recommended position: one-cycle hard cooldown. The
      model must use the strongest alternate position for the next forecast.

    The underlying probability estimates are not changed; this only controls
    which position Tianji chooses to publish.
    """
    adjusted = list(combined)
    base = max(range(10), key=lambda index: adjusted[index])
    if failed_position is None or miss_count < 2 or base != failed_position:
        return adjusted, base, "未触发换位保护"

    support = _review_support(reviews, base)
    if miss_count >= 3:
        adjusted[base] = -1.0
        selected = max(range(10), key=lambda index: adjusted[index])
        return (
            adjusted,
            selected,
            f"第{base + 1}名已连续推荐失败{miss_count}期，触发一周期硬冷却；"
            f"改用综合证据最强的第{selected + 1}名",
        )

    factor = 0.96 if support >= 2 else (0.90 if support == 1 else 0.84)
    adjusted[base] *= factor
    selected = max(range(10), key=lambda index: adjusted[index])
    if selected == base:
        return (
            adjusted,
            selected,
            f"第{base + 1}名连续推荐失败2期，已按AI支持度降权；证据仍明显领先，暂保留",
        )
    return (
        adjusted,
        selected,
        f"第{base + 1}名连续推荐失败2期且AI支持不足，降权后切换到第{selected + 1}名",
    )


def _analyze_with_failover(
    history: list[Any],
    target_period: str,
    config: Any,
    *,
    recent_positions: list[int] | None = None,
    strategy_weights: dict[str, float] | None = None,
) -> Any:
    del recent_positions, strategy_weights
    started = time.monotonic()
    profiles = tuple(
        fixed_target_runtime_guard._stable_position_profile(history, position)
        for position in range(10)
    )
    reviews = ai_ensemble._run_prefix_cached(
        fixed_target_bridge.TARGET_REVIEWERS,
        lambda reviewer: fixed_target_bridge._target_position_review(
            config,
            history=history,
            profiles=profiles,
            target_period=target_period,
            reviewer=reviewer,
        ),
    )
    math_scores = fixed_target_runtime_guard._normalize_scores(
        [profile.score for profile in profiles]
    )
    ai_scores = fixed_target_runtime_guard._normalize_scores([
        sum(review.scores[position] for review in reviews) / len(reviews)
        for position in range(10)
    ])
    combined = [
        math_scores[index] * MATH_WEIGHT + ai_scores[index] * AI_WEIGHT
        for index in range(10)
    ]

    failed_position, miss_count = _recent_failed_position_streak(history, str(config.model))
    adjusted, selected_index, failover_note = _apply_failover(
        combined,
        reviews,
        failed_position=failed_position,
        miss_count=miss_count,
    )
    ranking = sorted(range(10), key=lambda index: adjusted[index], reverse=True)
    selected = profiles[selected_index]
    runner_up = profiles[ranking[1]]

    ai_best = max(range(10), key=lambda index: ai_scores[index])
    ai_support = _review_support(reviews, selected_index)
    analyses = "；".join(review.analysis for review in reviews if review.analysis)[:240]
    analysis = (
        f"固定目标六码{fixed_target_bridge.TARGET_LABEL}，Top6始终为02/03/05/07/08/10；"
        "只预测下一期最值得关注的名次。"
        "使用24/60/120/240期分层收缩、192期衰减和最多120期严格前向验证。"
        "旧版数学证据权重68%已废弃；当前数学前向证据80%、3路AI评审20%，"
        "AI同时承担连续失败后的换位复核。"
        f"{failover_note}。最终第{selected.position + 1}名，"
        f"目标概率约{selected.target_probability * 100:.1f}%，"
        f"前向命中约{selected.validation_hit_rate * 100:.1f}%/{selected.validation_samples}期，"
        f"LogLoss {selected.average_log_loss:.3f}，Brier {selected.average_brier:.3f}；"
        f"第二候选第{runner_up.position + 1}名约{runner_up.target_probability * 100:.1f}%。"
        f"AI平均首选第{ai_best + 1}名，{ai_support}/{len(reviews)}路支持最终名次。"
        + (f" AI摘要：{analyses}" if analyses else "")
    )[:1200]
    risk_note = (
        "固定目标只有235780；任意固定位置的随机命中基准就是60%。"
        "连续推荐失败只用于判断天机自己的选位决策近期是否失效，不代表该位置下一期更该出或更不该出。"
        "三连败后的换位属于风险控制与防死磕机制，不保证提高随机开奖命中率。"
    )[:800]

    probabilities = selected.exact_probabilities
    top7 = fixed_target_bridge._top7(probabilities)
    usage = ai_ensemble._merge_usage(reviews)
    prompt_total = usage.get("prompt_cache_hit_tokens", 0) + usage.get("prompt_cache_miss_tokens", 0)
    cache_hit_rate = usage.get("prompt_cache_hit_tokens", 0) / prompt_total if prompt_total else 0.0
    strategy_name = f"ai_fixed_{fixed_target_bridge.TARGET_LABEL}_position_{selected.position + 1}"
    return ai_ensemble.AiEnsembleResult(
        position=selected.position,
        probabilities=probabilities,
        top6=list(_FIXED),
        top7=top7,
        analysis=analysis,
        risk_note=risk_note,
        latency_ms=int((time.monotonic() - started) * 1000),
        position_reviewers=len(reviews),
        number_reviewers=0,
        collapse_reviewed=(miss_count >= 2 and failed_position is not None),
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
    ai_ensemble.analyze_ensemble = _analyze_with_failover
    _INSTALLED = True
