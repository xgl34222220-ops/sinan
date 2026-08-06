from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
import re
import time
from typing import Any

from . import admin_insights, ai
from .db import database
from .runtime_config import RuntimeAiConfig, load_ai_config


_INSTALLED = False
_ORIGINAL_AI_ANALYZE = ai.analyze
_PERIOD_RE = re.compile(r"^(.*?)(\d+)$")
_AI_OVERLAP_AUDIT_THRESHOLD = 5
_AI_HOLDOUT_REVIEWERS = 3
_AI_HOLDOUT_MASK_RECENT = 14


def _record_group_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("lottery") or ""),
        str(record.get("source") or ""),
        str(record.get("model") or ""),
    )


def _period_sort_key(record: dict[str, Any]) -> tuple[str, int, int, int]:
    period = str(record.get("target_period") or "")
    match = _PERIOD_RE.match(period)
    prefix = match.group(1) if match else period
    number = int(match.group(2)) if match else -1
    created = int(record.get("created_at_epoch_ms") or 0)
    record_id = int(record.get("id") or 0)
    return prefix, number, created, record_id


def _canonical_grouped_rows(
    rows_desc: list[dict[str, Any]],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    seen: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for record in rows_desc:
        if record.get("top6_hit") is None:
            continue
        key = _record_group_key(record)
        target_period = str(record.get("target_period") or "")
        if not all(key) or not target_period or target_period in seen[key]:
            continue
        seen[key].add(target_period)
        grouped[key].append(record)
    for values in grouped.values():
        values.sort(key=_period_sort_key, reverse=True)
    return grouped


def _single_streak(rows_desc: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows_desc:
        return {"current_type": None, "current": 0, "longest_miss": 0}

    current_type = "hit" if rows_desc[0].get("top6_hit") is True else "miss"
    current = 0
    for record in rows_desc:
        record_type = "hit" if record.get("top6_hit") is True else "miss"
        if record_type != current_type:
            break
        current += 1

    longest_miss = 0
    running_miss = 0
    for record in reversed(rows_desc):
        if record.get("top6_hit") is True:
            running_miss = 0
        else:
            running_miss += 1
            longest_miss = max(longest_miss, running_miss)

    return {
        "current_type": current_type,
        "current": current,
        "longest_miss": longest_miss,
    }


def _leader_payload(
    key: tuple[str, str, str] | None,
    streak: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if key is None or streak is None:
        return None
    lottery, source, model = key
    return {
        "lottery": lottery,
        "lottery_name": (
            admin_insights.LOTTERIES[lottery].name
            if lottery in admin_insights.LOTTERIES
            else lottery
        ),
        "source": source,
        "source_name": "天机云端 AI" if source == "ai" else "天机云端本地",
        "model": model,
        **streak,
    }


def _scope_streak(rows_desc: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = _canonical_grouped_rows(rows_desc)
    if not grouped:
        return {
            "current_type": None,
            "current": 0,
            "longest_miss": 0,
            "group_count": 0,
            "current_leader": None,
            "longest_miss_leader": None,
        }

    streaks = {key: _single_streak(values) for key, values in grouped.items()}
    miss_current = [
        (key, value)
        for key, value in streaks.items()
        if value["current_type"] == "miss"
    ]
    if miss_current:
        current_key, current_streak = max(
            miss_current,
            key=lambda item: (
                int(item[1]["current"]),
                int(item[1]["longest_miss"]),
                item[0],
            ),
        )
    else:
        current_key, current_streak = max(
            streaks.items(),
            key=lambda item: (
                int(item[1]["current"]),
                int(item[1]["longest_miss"]),
                item[0],
            ),
        )

    longest_key, longest_streak = max(
        streaks.items(),
        key=lambda item: (
            int(item[1]["longest_miss"]),
            int(item[1]["current"]),
            item[0],
        ),
    )
    return {
        "current_type": current_streak["current_type"],
        "current": int(current_streak["current"]),
        "longest_miss": int(longest_streak["longest_miss"]),
        "group_count": len(grouped),
        "current_leader": _leader_payload(current_key, current_streak),
        "longest_miss_leader": _leader_payload(longest_key, longest_streak),
    }


def _group_summary_fixed(rows_desc: list[dict[str, Any]]) -> dict[str, Any]:
    settled = [row for row in rows_desc if row.get("top6_hit") is not None]
    windows: dict[str, Any] = {}
    for size in (20, 50, 100):
        scoped = settled[:size]
        value = admin_insights._rate(scoped)
        value["streak"] = _scope_streak(scoped)
        windows[str(size)] = value

    all_value = admin_insights._rate(rows_desc)
    all_value["streak"] = _scope_streak(rows_desc)
    windows["all"] = all_value

    position_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    latencies: list[float] = []
    for row in rows_desc:
        position_rows[int(row.get("position") or 0)].append(row)
        match = admin_insights._LATENCY_RE.search(str(row.get("analysis") or ""))
        if match:
            latencies.append(float(match.group(1)))

    positions = []
    for position in range(10):
        value = admin_insights._rate(position_rows.get(position, []))
        value["position"] = position
        value["streak"] = _scope_streak(position_rows.get(position, []))
        positions.append(value)

    return {
        **admin_insights._rate(rows_desc),
        "windows": windows,
        "streak": _scope_streak(rows_desc),
        "positions": positions,
        "average_latency_seconds": (
            round(sum(latencies) / len(latencies), 2) if latencies else None
        ),
    }


def _top6_overlap(left: list[int], right: list[int]) -> int:
    return len(set(int(value) for value in left) & set(int(value) for value in right))


def _requires_independence_audit(
    ai_top6: list[int],
    native_top6: list[int],
) -> bool:
    return _top6_overlap(ai_top6, native_top6) >= _AI_OVERLAP_AUDIT_THRESHOLD


def _native_reference(lottery: str, target_period: str) -> Any | None:
    for forecast in database.list_forecasts(lottery, 80):
        if (
            forecast.source == "native"
            and forecast.target_period == target_period
            and len(forecast.top6) == 6
        ):
            return forecast
    return None


def _audit_ai_prediction(
    result: Any,
    *,
    history: list[Any],
    target_period: str,
    active: RuntimeAiConfig,
    native_reference: Any,
) -> Any:
    from . import ai_ensemble

    initial_overlap = _top6_overlap(result.top6, native_reference.top6)
    if initial_overlap < _AI_OVERLAP_AUDIT_THRESHOLD:
        return result

    mask_recent = min(
        _AI_HOLDOUT_MASK_RECENT,
        max(0, len(ai_ensemble._canonical_history(history)) - 30),
    )
    if mask_recent < 7:
        raise RuntimeError(
            "AI 与本地结果高度重合，但历史样本不足以完成独立留出复核，本期 AI 不入库"
        )

    audit_started = time.monotonic()
    audit_results = ai_ensemble._run_prefix_cached(
        _AI_HOLDOUT_REVIEWERS,
        lambda reviewer: ai_ensemble._number_review(
            active,
            history=history,
            position=result.position,
            target_period=target_period,
            trained_through_period=history[-1].period,
            reviewer=reviewer + 500,
            mask_recent=mask_recent,
        ),
    )
    probabilities = ai_ensemble._aggregate(audit_results)
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
    audited_top6 = [index + 1 for index in ranked[:6]]
    audited_top7 = [index + 1 for index in ranked[:7]]
    final_overlap = _top6_overlap(audited_top6, native_reference.top6)

    if final_overlap == 6:
        raise RuntimeError(
            "AI 独立性审计未通过：隐藏近期数据复核后仍与本地六码完全一致，本期结果已拒绝入库"
        )

    usage = ai_ensemble._merge_usage(audit_results)
    prompt_tokens = int(result.prompt_tokens) + int(usage["prompt_tokens"])
    cache_hit_tokens = int(result.prompt_cache_hit_tokens) + int(
        usage["prompt_cache_hit_tokens"]
    )
    cache_miss_tokens = int(result.prompt_cache_miss_tokens) + int(
        usage["prompt_cache_miss_tokens"]
    )
    cache_total = cache_hit_tokens + cache_miss_tokens
    cache_hit_rate = cache_hit_tokens / cache_total if cache_total else 0.0
    strategies = {
        f"ai_independence_holdout_{index + 1}": ai_ensemble._normalize(review.scores)
        for index, review in enumerate(audit_results)
    }
    equal_weight = 1.0 / len(strategies)
    weights = {name: equal_weight for name in strategies}

    audit_ms = int((time.monotonic() - audit_started) * 1000)
    analysis = (
        f"{result.analysis} 与同目标期本地模型六码重合 {initial_overlap}/6，"
        f"已隐藏最近 {mask_recent} 期并执行 {_AI_HOLDOUT_REVIEWERS} 路独立复核；"
        f"复核后重合 {final_overlap}/6，最终号码仅采用独立留出评审。"
    )[:900]
    risk_note = (
        f"{result.risk_note} 已启用跨来源独立性审计；"
        "AI 与本地结果完全重合且无法通过留出复核时，不再写入正式 AI 档案。"
    )[:520]

    return replace(
        result,
        probabilities=probabilities,
        top6=audited_top6,
        top7=audited_top7,
        analysis=analysis,
        risk_note=risk_note,
        latency_ms=int(result.latency_ms) + audit_ms,
        request_count=int(result.request_count) + int(usage["request_count"]),
        prompt_tokens=prompt_tokens,
        prompt_cache_hit_tokens=cache_hit_tokens,
        prompt_cache_miss_tokens=cache_miss_tokens,
        completion_tokens=int(result.completion_tokens)
        + int(usage["completion_tokens"]),
        reasoning_tokens=int(result.reasoning_tokens) + int(usage["reasoning_tokens"]),
        cache_hit_rate=round(cache_hit_rate, 6),
        strategy_probabilities=strategies,
        strategy_weights=weights,
    )


def _analyze_with_independence(
    history: list[Any],
    target_period: str,
    config: RuntimeAiConfig | None = None,
    *,
    recent_positions: list[int] | None = None,
    strategy_weights: dict[str, float] | None = None,
) -> Any:
    result = _ORIGINAL_AI_ANALYZE(
        history,
        target_period,
        config,
        recent_positions=recent_positions,
        strategy_weights=strategy_weights,
    )
    if not history:
        return result
    lottery = str(getattr(history[-1], "lottery", "") or "")
    if not lottery:
        return result
    native_reference = _native_reference(lottery, target_period)
    if native_reference is None:
        return result
    active = config or load_ai_config()
    return _audit_ai_prediction(
        result,
        history=history,
        target_period=target_period,
        active=active,
        native_reference=native_reference,
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    admin_insights._group_summary = _group_summary_fixed
    ai.analyze = _analyze_with_independence
    _INSTALLED = True
