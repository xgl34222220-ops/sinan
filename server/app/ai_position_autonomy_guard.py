from __future__ import annotations

import time
from typing import Any

from . import ai_ensemble, fixed_target_bridge, fixed_target_runtime_guard
from .db import database


_FIXED = tuple(fixed_target_bridge.TARGET_NUMBERS)
_WINDOWS = (24, 60, 120, 240)
_REVIEWER_ROLES = (
    (
        "short_term_trend",
        "重点分析最近24/60期实际号码序列、235780命中斜率、冷热切换、当前号码后的状态转移；"
        "不要因为一两期波动就下结论，也不要机械追涨杀跌。",
    ),
    (
        "medium_long_validation",
        "重点分析120/240期结构、窗口稳定性、最多120期严格前向命中率、LogLoss与Brier；"
        "优先可重复的中长期证据，主动识别短期假趋势。",
    ),
    (
        "self_correction",
        "重点复盘天机AI自己最近真实选位及结算结果，检查是否对某候选形成锚定、惯性或过度自信；"
        "同时结合完整实际号码走势判断是否仍应坚持原候选。",
    ),
)
_INSTALLED = False


def _is_target(number: int) -> bool:
    return int(number) in _FIXED


def _recent_ai_decisions(history: list[Any], model: str, limit: int = 20) -> list[dict[str, Any]]:
    if not history:
        return []
    lottery = str(getattr(history[-1], "lottery", ""))
    if not lottery:
        return []
    rows = database.list_forecasts(lottery, max(30, limit * 2))
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
                "actual_number": int(actual),
                "hit_fixed_235780": bool(hit),
            }
        )
        if len(result) >= limit:
            break
    return result


def _rate(values: list[int]) -> float:
    if not values:
        return fixed_target_bridge.RANDOM_BASELINE
    return sum(_is_target(value) for value in values) / len(values)


def _count_vector(values: list[int]) -> list[int]:
    return [sum(1 for value in values if value == number) for number in range(1, 11)]


def _target_streak(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"state": "none", "length": 0}
    current_hit = _is_target(values[-1])
    length = 0
    for value in reversed(values):
        if _is_target(value) != current_hit:
            break
        length += 1
    return {"state": "hit" if current_hit else "miss", "length": length}


def _transition_features(values: list[int]) -> dict[str, Any]:
    if len(values) < 2:
        return {
            "current_number": values[-1] if values else None,
            "successor_samples": 0,
            "successor_target_rate": fixed_target_bridge.RANDOM_BASELINE,
            "successor_number_counts_1_to_10": [0] * 10,
            "same_target_state_samples": 0,
            "same_target_state_next_hit_rate": fixed_target_bridge.RANDOM_BASELINE,
        }

    current = values[-1]
    successor_numbers: list[int] = []
    state_samples = 0
    state_hits = 0
    current_state = _is_target(current)
    for index in range(1, len(values)):
        if values[index - 1] == current:
            successor_numbers.append(values[index])
        if _is_target(values[index - 1]) == current_state:
            state_samples += 1
            state_hits += int(_is_target(values[index]))
    return {
        "current_number": current,
        "successor_samples": len(successor_numbers),
        "successor_target_rate": round(_rate(successor_numbers), 6),
        "successor_number_counts_1_to_10": _count_vector(successor_numbers),
        "same_target_state_samples": state_samples,
        "same_target_state_next_hit_rate": round(
            state_hits / state_samples if state_samples else fixed_target_bridge.RANDOM_BASELINE,
            6,
        ),
    }


def _trend_evidence(
    history: list[Any],
    profiles: tuple[Any, ...],
) -> list[dict[str, Any]]:
    verified = fixed_target_bridge._canonical(history, 360)
    evidence: list[dict[str, Any]] = []
    for position, profile in enumerate(profiles):
        values = [draw.numbers[position] for draw in verified]
        window_rates: dict[str, float] = {}
        number_counts: dict[str, list[int]] = {}
        for size in _WINDOWS:
            subset = values[-min(size, len(values)) :]
            window_rates[str(size)] = round(_rate(subset), 6)
            number_counts[str(size)] = _count_vector(subset)

        recent24 = values[-min(24, len(values)) :]
        recent60 = values[-min(60, len(values)) :]
        evidence.append(
            {
                "position": position + 1,
                "current_target_probability": round(float(profile.target_probability), 6),
                "validation_samples": int(profile.validation_samples),
                "validation_hit_rate": round(float(profile.validation_hit_rate), 6),
                "excess_over_random_60pct": round(
                    float(profile.validation_hit_rate) - fixed_target_bridge.RANDOM_BASELINE,
                    6,
                ),
                "average_binary_log_loss": round(float(profile.average_log_loss), 6),
                "average_brier": round(float(profile.average_brier), 6),
                "longest_miss_streak": int(profile.max_miss_streak),
                "current_miss_streak": int(profile.current_miss_streak),
                "window_target_hit_rates": window_rates,
                "window_number_counts_1_to_10": number_counts,
                "trend_deltas": {
                    "rate24_minus_rate60": round(window_rates["24"] - window_rates["60"], 6),
                    "rate60_minus_rate120": round(window_rates["60"] - window_rates["120"], 6),
                    "rate120_minus_rate240": round(window_rates["120"] - window_rates["240"], 6),
                },
                "recent_actual_numbers_newest_to_oldest": list(reversed(recent24)),
                "recent_target_hits_newest_to_oldest": [
                    int(_is_target(value)) for value in reversed(recent60)
                ],
                "current_target_streak": _target_streak(values),
                "transitions": _transition_features(values),
            }
        )
    return evidence


def _full_trend_history(
    history: list[Any],
    neutral_mapping: dict[str, int],
) -> dict[str, Any]:
    verified = fixed_target_bridge._canonical(history, 240)
    return {
        "periods_oldest_to_newest": [draw.period for draw in verified],
        "actual_numbers_by_candidate_oldest_to_newest": {
            neutral_id: [draw.numbers[position] for draw in verified]
            for neutral_id, position in neutral_mapping.items()
        },
        "target_hits_by_candidate_oldest_to_newest": {
            neutral_id: [int(_is_target(draw.numbers[position])) for draw in verified]
            for neutral_id, position in neutral_mapping.items()
        },
    }


def _decision_history_for_mapping(
    recent_decisions: list[dict[str, Any]],
    neutral_by_actual: dict[int, str],
) -> list[dict[str, Any]]:
    return [
        {
            "target_period": row["target_period"],
            "selected_candidate": neutral_by_actual.get(
                int(row["selected_position"]) - 1,
                "unknown",
            ),
            "actual_number": int(row["actual_number"]),
            "hit_fixed_235780": bool(row["hit_fixed_235780"]),
        }
        for row in recent_decisions
    ]


def _ai_consensus(reviews: list[Any]) -> tuple[list[float], int, list[int]]:
    """Diagnostic consensus only; the final published position is chosen by the AI arbiter."""
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
    evidence = _trend_evidence(history, profiles)
    shared_candidates, neutral_mapping, neutral_by_actual = ai_ensemble._shared_anonymized_items(
        evidence,
        target_period=target_period,
        phase="fixed-235780-full-trend-shared",
    )
    _, reviewer_mapping = ai_ensemble._anonymized_items(
        evidence,
        target_period=target_period,
        phase="fixed-235780-full-trend-review",
        reviewer=reviewer,
    )
    trained_through = fixed_target_bridge._canonical(history, 240)[-1].period
    role_name, role_instruction = _REVIEWER_ROLES[reviewer % len(_REVIEWER_ROLES)]
    prompt = (
        "你是天机云端AI的235780名次走势专家。唯一固定目标是235780，内部集合2/3/5/7/8/10，0代表10；"
        "禁止生成、替换或优化这组六码。你的任务是预测下一期十个匿名位置中，哪个位置最可能落入固定集合。"
        "这次不能只看0/1命中序列：共享数据同时包含最多240期每个匿名位置的真实1至10号码序列、"
        "对应235780命中序列、24/60/120/240窗口命中率和号码分布、窗口趋势差、当前号码后的转移、"
        "最多120期严格前向命中率、LogLoss、Brier、连续状态，以及天机AI自己最近真实选位和结算。"
        "必须比较十个候选的走势变化、稳定性和失效迹象，而不是锚定上一次答案。"
        "严禁使用‘连续没出所以该出’或‘连续失败所以必须换’这种人工规则；失败只是证据，是否继续同一位置由走势决定。"
        "每个位置随机命中固定235780的理论基准是60%，不要把随机波动包装成规律。"
        "只返回紧凑JSON：{\"scores\":{\"A\":数值,...,\"J\":数值},"
        "\"selected\":\"A至J之一\",\"analysis\":\"不超过160字简体中文，明确说明关键走势依据\"}。"
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
            "evidence_mode": "full_actual_number_trend_plus_target_membership_and_forward_validation",
            "neutral_full_trend_history": _full_trend_history(history, neutral_mapping),
            "neutral_candidates": shared_candidates,
            "recent_ai_decision_outcomes": _decision_history_for_mapping(
                recent_decisions,
                neutral_by_actual,
            ),
        },
        reviewer_payload={
            "reviewer": reviewer + 1,
            "independent_review": True,
            "reviewer_role": role_name,
            "candidate_aliases_A_to_J": ai_ensemble._reviewer_aliases(
                reviewer_mapping,
                neutral_by_actual,
            ),
            "review_instruction": role_instruction,
        },
        max_tokens=1200,
        timeout_seconds=50,
    )
    return ai_ensemble._parse_label_scores(result, reviewer_mapping)


def _final_judge(
    config: Any,
    *,
    history: list[Any],
    profiles: tuple[Any, ...],
    target_period: str,
    reviews: list[Any],
    recent_decisions: list[dict[str, Any]],
) -> Any:
    evidence = _trend_evidence(history, profiles)
    judge_candidates, judge_mapping = ai_ensemble._anonymized_items(
        evidence,
        target_period=target_period,
        phase="fixed-235780-final-arbiter",
        reviewer=0,
    )
    label_by_actual = {actual: label for label, actual in judge_mapping.items()}
    reviewer_opinions: list[dict[str, Any]] = []
    for index, review in enumerate(reviews):
        scores = {
            label_by_actual[position]: round(float(review.scores[position]), 6)
            for position in range(10)
        }
        reviewer_opinions.append(
            {
                "role": _REVIEWER_ROLES[index % len(_REVIEWER_ROLES)][0],
                "scores": scores,
                "analysis": str(getattr(review, "analysis", ""))[:220],
            }
        )
    judge_decisions = [
        {
            "target_period": row["target_period"],
            "selected_candidate": label_by_actual.get(
                int(row["selected_position"]) - 1,
                "unknown",
            ),
            "actual_number": int(row["actual_number"]),
            "hit_fixed_235780": bool(row["hit_fixed_235780"]),
        }
        for row in recent_decisions
    ]
    result = ai_ensemble._call_json(
        config,
        system_prompt=(
            "你是天机云端AI的最终走势裁判。固定目标永远是235780（内部2/3/5/7/8/10），只决定下一期最值得选的一个名次。"
            "你会看到十个匿名候选的完整趋势摘要、三位不同职责AI专家的独立评分与理由、以及AI自身近期真实实战结果。"
            "不要简单做多数投票，也不要机械平均；要审查三路意见是否被短期噪声、长期滞后或历史锚定误导，"
            "结合候选自身24/60/120/240走势与严格前向指标作最终判断。没有任何轮换、禁选、冷却或连续失败硬规则。"
            "如果同一候选证据仍最强可以继续选；如果走势已经恶化就应主动换。随机基准60%，不得宣称确定规律。"
            "只返回紧凑JSON：{\"scores\":{\"A\":数值,...,\"J\":数值},"
            "\"selected\":\"A至J之一\",\"analysis\":\"不超过180字简体中文，说明为何最终选择该候选\"}。"
        ),
        shared_payload={
            "target_period": target_period,
            "fixed_target": fixed_target_bridge.TARGET_LABEL,
            "random_position_baseline": fixed_target_bridge.RANDOM_BASELINE,
            "candidate_trend_summaries": judge_candidates,
            "specialist_reviews": reviewer_opinions,
            "recent_ai_decision_outcomes": judge_decisions,
        },
        reviewer_payload={
            "role": "final_trend_arbiter",
            "instruction": "独立综合三路专家与趋势证据，最终选一个候选；不得套用人工换位规则。",
        },
        max_tokens=1100,
        timeout_seconds=45,
    )
    return ai_ensemble._parse_label_scores(result, judge_mapping)


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
        len(_REVIEWER_ROLES),
        lambda reviewer: _autonomous_review(
            config,
            history=history,
            profiles=profiles,
            target_period=target_period,
            reviewer=reviewer,
            recent_decisions=recent_decisions,
        ),
    )
    judge = _final_judge(
        config,
        history=history,
        profiles=profiles,
        target_period=target_period,
        reviews=reviews,
        recent_decisions=recent_decisions,
    )
    judge_scores = fixed_target_runtime_guard._normalize_scores(list(judge.scores))
    ranking = sorted(range(10), key=lambda index: judge_scores[index], reverse=True)
    selected_index = ranking[0]
    selected = profiles[selected_index]
    runner_up = profiles[ranking[1]]
    specialist_support = sum(
        max(range(10), key=lambda index: review.scores[index]) == selected_index
        for review in reviews
    )
    specialist_analyses = "；".join(
        str(review.analysis) for review in reviews if getattr(review, "analysis", "")
    )[:420]
    analysis = (
        f"固定目标六码{fixed_target_bridge.TARGET_LABEL}，Top6始终为02/03/05/07/08/10。"
        "本期使用完整走势AI：最多240期真实号码时序+235780命中时序，逐位置展开24/60/120/240窗口、"
        "号码分布与趋势差、状态转移、最多120期严格前向验证、LogLoss/Brier及AI最近真实实战。"
        "三路专家分别负责短期走势、中长期验证、自我纠错，最后由第四路AI总裁判直接决定名次；"
        "没有人工轮换、降权、禁选或冷却规则。"
        f"最终选择第{selected.position + 1}名，三路专家中{specialist_support}/{len(reviews)}路首选该名次；"
        f"该位置统计目标概率约{selected.target_probability * 100:.1f}%，前向命中约"
        f"{selected.validation_hit_rate * 100:.1f}%/{selected.validation_samples}期。"
        f"AI第二候选第{runner_up.position + 1}名。总裁判：{judge.analysis}"
        + (f" 专家摘要：{specialist_analyses}" if specialist_analyses else "")
    )[:1500]
    risk_note = (
        "固定235780覆盖10个位置中的6个，任意固定位置随机命中基准为60%。"
        "完整实际号码走势能减少信息损失和锚定，但若开奖接近独立随机，AI仍无法可靠预知下一期；"
        "因此不承诺稳定高于60%或连续命中。"
    )[:800]

    probabilities = selected.exact_probabilities
    top7 = fixed_target_bridge._top7(probabilities)
    usage = ai_ensemble._merge_usage([*reviews, judge])
    prompt_total = usage.get("prompt_cache_hit_tokens", 0) + usage.get("prompt_cache_miss_tokens", 0)
    cache_hit_rate = usage.get("prompt_cache_hit_tokens", 0) / prompt_total if prompt_total else 0.0
    strategy_name = f"ai_fixed_{fixed_target_bridge.TARGET_LABEL}_full_trend_position_{selected.position + 1}"
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
