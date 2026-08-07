from __future__ import annotations

import time
from typing import Any

from . import ai_ensemble, fixed_target_bridge, fixed_target_runtime_guard
from .db import database


_FIXED = tuple(fixed_target_bridge.TARGET_NUMBERS)
_INSTALLED = False


def _recent_ai_decisions(history: list[Any], model: str, limit: int = 12) -> list[dict[str, Any]]:
    if not history:
        return []
    lottery = str(getattr(history[-1], "lottery", ""))
    if not lottery:
        return []
    rows = database.list_forecasts(lottery, max(20, limit * 2))
    result: list[dict[str, Any]] = []
    for forecast in rows:
        if str(getattr(forecast, "source", "")) != "ai":
            continue
        if str(getattr(forecast, "model", "")) != model:
            continue
        hit = getattr(forecast, "top6_hit", None)
        actual = getattr(forecast, "actual_number", None)
        if hit is None or actual is None:
            continue
        result.append(
            {
                "target_period": str(getattr(forecast, "target_period", "")),
                "selected_position": int(getattr(forecast, "position")) + 1,
                "hit_fixed_235780": bool(hit),
            }
        )
        if len(result) >= limit:
            break
    return result


def _ai_consensus(reviews: list[Any]) -> tuple[list[float], int, list[int]]:
    if not reviews:
        raise ValueError("AI名次评审为空")
    for review in reviews:
        if len(list(getattr(review, "scores", []) or [])) != 10:
            raise ValueError("AI名次评审未返回完整10位置评分")
    scores = fixed_target_runtime_guard._normalize_scores([
        sum(float(review.scores[position]) for review in reviews) / len(reviews)
        for position in range(10)
    ])
    ranking = sorted(range(10), key=lambda index: scores[index], reverse=True)
    return scores, ranking[0], ranking


def _autonomous_review(
    config: Any,
    *,
    history: list[Any],
    profiles: tuple[Any, ...],
    target_period: str,
    reviewer: int,
    recent_decisions: list[dict[str, Any]],
) -> Any:
    evidence = [fixed_target_bridge._profile_evidence(profile) for profile in profiles]
    shared_candidates, neutral_mapping, neutral_by_actual = ai_ensemble._shared_anonymized_items(
        evidence,
        target_period=target_period,
        phase="fixed-235780-autonomy-shared",
    )
    _, reviewer_mapping = ai_ensemble._anonymized_items(
        evidence,
        target_period=target_period,
        phase="fixed-235780-autonomy-review",
        reviewer=reviewer,
    )
    trained_through = fixed_target_bridge._canonical(history, 120)[-1].period
    decision_history = [
        {
            "target_period": row["target_period"],
            "selected_candidate": neutral_by_actual.get(int(row["selected_position"]) - 1, "unknown"),
            "hit_fixed_235780": bool(row["hit_fixed_235780"]),
        }
        for row in recent_decisions
    ]
    prompt = (
        "你是天机云端AI的最终名次判断者。唯一固定目标是235780，内部集合2/3/5/7/8/10，0代表10；"
        "禁止生成或替换这组六码。你的任务只有一个：独立判断下一期十个匿名位置中，哪一个最可能落入固定集合。"
        "你拥有完整匿名0/1历史、24/60/120/240期统计、严格前向命中率、LogLoss、Brier、当前连续不中，"
        "以及天机AI自己最近若干次选位及真实结算结果。请把这些都当证据，不使用任何人工轮换、冷却、"
        "连续不中必反弹、连续不中必换位等硬规则。每一期都从头比较十个候选；若上期选择失败，要重新审视"
        "原判断是否仍有充分证据，避免锚定，但如果证据仍然最强也允许继续选同一位置。随机基准是60%，"
        "不要把随机波动包装成确定规律。只返回紧凑JSON："
        "{\"scores\":{\"A\":数值,...,\"J\":数值},\"selected\":\"A至J之一\","
        "\"analysis\":\"不超过140字简体中文，说明最关键的比较依据\"}。"
    )
    result = ai_ensemble._call_json(
        config,
        system_prompt=prompt,
        shared_payload={
            "target_period": target_period,
            "trained_through_period": trained_through,
            "fixed_target": fixed_target_bridge.TARGET_LABEL,
            "internal_target_numbers": list(_FIXED),
            "random_position_baseline": fixed_target_bridge.RANDOM_BASELINE,
            "history_order": "oldest_to_newest",
            "neutral_target_membership_history": fixed_target_bridge._target_membership_history(
                history, neutral_mapping
            ),
            "neutral_candidates": shared_candidates,
            "recent_ai_decision_outcomes": decision_history,
        },
        reviewer_payload={
            "reviewer": reviewer + 1,
            "independent_review": True,
            "candidate_aliases_A_to_J": ai_ensemble._reviewer_aliases(
                reviewer_mapping,
                neutral_by_actual,
            ),
            "review_instruction": (
                "独立给十个候选打分并选出下一期最值得推荐的位置。"
                "不要机械延续上一期，也不要机械轮换；以全部证据自行决策。"
            ),
        },
        max_tokens=1000,
        timeout_seconds=45,
    )
    return ai_ensemble._parse_label_scores(result, reviewer_mapping)


def _analyze_ai_autonomy(
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
    recent_decisions = _recent_ai_decisions(history, str(config.model))
    reviews = ai_ensemble._run_prefix_cached(
        fixed_target_bridge.TARGET_REVIEWERS,
        lambda reviewer: _autonomous_review(
            config,
            history=history,
            profiles=profiles,
            target_period=target_period,
            reviewer=reviewer,
            recent_decisions=recent_decisions,
        ),
    )
    ai_scores, selected_index, ranking = _ai_consensus(reviews)
    selected = profiles[selected_index]
    runner_up = profiles[ranking[1]]
    ai_support = sum(
        max(range(10), key=lambda index: review.scores[index]) == selected_index
        for review in reviews
    )
    analyses = "；".join(review.analysis for review in reviews if review.analysis)[:360]
    analysis = (
        f"固定目标六码{fixed_target_bridge.TARGET_LABEL}，Top6始终为02/03/05/07/08/10。"
        "最终名次由3路AI独立复核后的共识直接决定，不再设置人工轮换、降权、禁选或冷却规则；"
        "24/60/120/240期统计、最多120期严格前向验证、LogLoss、Brier、当前连续不中和AI自身最近实战"
        "结算全部作为AI输入证据。"
        f"本期AI共识选择第{selected.position + 1}名，{ai_support}/{len(reviews)}路首选该名次；"
        f"该位置统计目标概率约{selected.target_probability * 100:.1f}%，前向命中约"
        f"{selected.validation_hit_rate * 100:.1f}%/{selected.validation_samples}期；"
        f"AI第二候选第{runner_up.position + 1}名。"
        + (f" AI摘要：{analyses}" if analyses else "")
    )[:1200]
    risk_note = (
        "固定235780覆盖10个位置中的6个，任意固定位置随机命中基准为60%。"
        "AI会根据历史和自身已结算表现重新判断，但开奖若接近随机，AI也无法可靠预知下一期；"
        "因此不承诺稳定高于60%或连续命中。"
    )[:800]

    probabilities = selected.exact_probabilities
    top7 = fixed_target_bridge._top7(probabilities)
    usage = ai_ensemble._merge_usage(reviews)
    prompt_total = usage.get("prompt_cache_hit_tokens", 0) + usage.get("prompt_cache_miss_tokens", 0)
    cache_hit_rate = usage.get("prompt_cache_hit_tokens", 0) / prompt_total if prompt_total else 0.0
    strategy_name = f"ai_fixed_{fixed_target_bridge.TARGET_LABEL}_autonomy_position_{selected.position + 1}"
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
    ai_ensemble.analyze_ensemble = _analyze_ai_autonomy
    _INSTALLED = True
