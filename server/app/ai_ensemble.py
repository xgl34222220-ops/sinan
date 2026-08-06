from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import hashlib
import json
import math
import random
import re
import time
from typing import Any

import httpx

from .adaptive_learning import (
    blend_strategy_probabilities,
    normalize_strategy_weights,
)
from .forecast_quality import (
    blend_probabilities as blend_validated_probabilities,
    position_quality_profile,
    recent_copy_diagnostics,
    regularize_recent_copy,
    statistical_components,
    statistical_probabilities,
)
from .models import DrawModel, compact_json
from .runtime_config import RuntimeAiConfig


_LABELS = tuple("ABCDEFGHIJ")
_POSITION_REVIEWERS = 3
_NUMBER_REVIEWERS = 2
_MAX_ATTEMPTS_PER_REVIEWER = 2
_RECENT_COPY_WINDOW = 7
_HOLDOUT_REVIEW_WEIGHT = 0.70


@dataclass(frozen=True)
class AiEnsembleResult:
    position: int
    probabilities: list[float]
    top6: list[int]
    top7: list[int]
    analysis: str
    risk_note: str
    latency_ms: int
    position_reviewers: int
    number_reviewers: int
    collapse_reviewed: bool
    recent_copy_reviewed: bool
    request_count: int
    prompt_tokens: int
    prompt_cache_hit_tokens: int
    prompt_cache_miss_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    cache_hit_rate: float
    strategy_probabilities: dict[str, list[float]] = field(default_factory=dict)
    strategy_weights: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class _ReviewerResult:
    scores: list[float]
    analysis: str
    usage: dict[str, int] = field(default_factory=dict)


def _usage_from_response(payload: dict[str, Any]) -> dict[str, int]:
    raw = payload.get("usage")
    usage = raw if isinstance(raw, dict) else {}
    details = usage.get("completion_tokens_details")
    completion_details = details if isinstance(details, dict) else {}
    hit = max(0, int(usage.get("prompt_cache_hit_tokens") or 0))
    miss = max(0, int(usage.get("prompt_cache_miss_tokens") or 0))
    prompt = max(0, int(usage.get("prompt_tokens") or hit + miss))
    completion = max(0, int(usage.get("completion_tokens") or 0))
    total = max(0, int(usage.get("total_tokens") or prompt + completion))
    reasoning = max(0, int(completion_details.get("reasoning_tokens") or 0))
    return {
        "request_count": 1,
        "prompt_tokens": prompt,
        "prompt_cache_hit_tokens": hit,
        "prompt_cache_miss_tokens": miss,
        "completion_tokens": completion,
        "reasoning_tokens": reasoning,
        "total_tokens": total,
    }


def _merge_usage(results: list[_ReviewerResult]) -> dict[str, int]:
    keys = (
        "request_count",
        "prompt_tokens",
        "prompt_cache_hit_tokens",
        "prompt_cache_miss_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "total_tokens",
    )
    return {
        key: sum(max(0, int(result.usage.get(key, 0))) for result in results)
        for key in keys
    }


def _normalize(values: list[float]) -> list[float]:
    safe = [value if math.isfinite(value) and value >= 0 else 0.0 for value in values]
    total = sum(safe)
    if total <= 0:
        raise ValueError("AI 评分全部为零")
    return [value / total for value in safe]


def _response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return str(message["content"])
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text
    output = payload.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(str(part["text"]))
        if parts:
            return "\n".join(parts)
    return ""


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        value = json.loads(stripped[start : end + 1])
        if isinstance(value, dict):
            return value
    raise ValueError("AI 未返回有效 JSON")


def _headers(config: RuntimeAiConfig) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _is_official_deepseek(config: RuntimeAiConfig) -> bool:
    endpoint = config.endpoint.lower()
    return "api.deepseek.com" in endpoint and config.model.lower().startswith("deepseek-")


def _call_json(
    config: RuntimeAiConfig,
    *,
    system_prompt: str,
    user_payload: dict[str, Any] | None = None,
    shared_payload: dict[str, Any] | None = None,
    reviewer_payload: dict[str, Any] | None = None,
    max_tokens: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    endpoint = config.endpoint.rstrip("/")
    is_responses = endpoint.endswith("/responses")
    if shared_payload is not None:
        user_content = (
            "共享预测证据（同一批次各路评审完全一致）：\n"
            + compact_json(shared_payload)
            + "\n\n本路独立评审参数：\n"
            + compact_json(reviewer_payload or {})
        )
    else:
        user_content = compact_json(user_payload or {})
    if is_responses:
        body: dict[str, Any] = {
            "model": config.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_output_tokens": max_tokens,
        }
    else:
        body = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
            "stream": False,
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
        }

    last_error: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS_PER_REVIEWER):
        request_body = dict(body)
        if attempt > 0 and not is_responses:
            request_body.pop("response_format", None)
            request_body["max_tokens"] = max_tokens + 400
            if _is_official_deepseek(config):
                request_body["thinking"] = {"type": "disabled"}
        try:
            attempt_timeout = timeout_seconds if attempt == 0 else min(30, timeout_seconds)
            with httpx.Client(
                timeout=httpx.Timeout(
                    attempt_timeout,
                    connect=min(12.0, attempt_timeout),
                ),
                follow_redirects=True,
            ) as client:
                response = client.post(
                    endpoint,
                    headers=_headers(config),
                    json=request_body,
                )
                if (
                    response.status_code >= 400
                    and not is_responses
                    and "response_format" in request_body
                ):
                    retry = dict(request_body)
                    retry.pop("response_format", None)
                    response = client.post(endpoint, headers=_headers(config), json=retry)
                response.raise_for_status()
                payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("AI 接口返回格式异常")
            response_text = _response_text(payload).strip()
            if not response_text:
                raise ValueError("AI 最终正文为空")
            parsed = _extract_json(response_text)
            parsed["_tianji_usage"] = _usage_from_response(payload)
            return parsed
        except Exception as exc:  # noqa: BLE001 - provider failures must be retried
            last_error = exc
    raise RuntimeError(f"AI 独立评审失败：{str(last_error)[:240]}")


def _canonical_history(history: list[DrawModel]) -> list[DrawModel]:
    verified = [
        draw
        for draw in history
        if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
    ]
    return verified[-120:]


def _history_scope(
    history: list[DrawModel],
    *,
    mask_recent: int = 0,
) -> list[DrawModel]:
    verified = _canonical_history(history)
    if mask_recent <= 0:
        return verified
    if len(verified) - mask_recent < 30:
        raise ValueError("隐藏近期样本后不足30期，无法进行独立复核")
    return verified[:-mask_recent]


def _counts(values: list[int], window: int) -> list[int]:
    result = [0] * 10
    for number in values[-window:]:
        if 1 <= number <= 10:
            result[number - 1] += 1
    return result


def _omission(values: list[int]) -> list[int]:
    result: list[int] = []
    for number in range(1, 11):
        index = -1
        for cursor in range(len(values) - 1, -1, -1):
            if values[cursor] == number:
                index = cursor
                break
        result.append(len(values) if index < 0 else len(values) - 1 - index)
    return result


def build_position_evidence(history: list[DrawModel]) -> list[dict[str, Any]]:
    verified = _canonical_history(history)
    if len(verified) < 30:
        raise ValueError("AI 预测至少需要30期有效历史")
    evidence: list[dict[str, Any]] = []
    for position in range(10):
        values = [draw.numbers[position] for draw in verified]
        count20 = _counts(values, 20)
        count60 = _counts(values, 60)
        count120 = _counts(values, 120)
        current = values[-1]
        successors = [0] * 10
        transition_samples = 0
        for index in range(1, len(values)):
            if values[index - 1] == current:
                successors[values[index] - 1] += 1
                transition_samples += 1
        drift = sum(
            abs(
                count20[index] / min(20, len(values))
                - count60[index] / min(60, len(values))
            )
            for index in range(10)
        ) / 10.0
        long_drift = sum(
            abs(
                count60[index] / min(60, len(values))
                - count120[index] / len(values)
            )
            for index in range(10)
        ) / 10.0
        evidence.append(
            {
                "position": position + 1,
                "latest_12_newest_to_oldest": list(reversed(values[-12:])),
                "count_20_by_number_1_to_10": count20,
                "count_60_by_number_1_to_10": count60,
                "count_120_by_number_1_to_10": count120,
                "omission_by_number_1_to_10": _omission(values),
                "current_number": current,
                "successor_count_after_current_by_number_1_to_10": successors,
                "successor_sample_size": transition_samples,
                "short_medium_drift": round(drift, 6),
                "medium_long_drift": round(long_drift, 6),
            }
        )
    return evidence


def _seed(target_period: str, phase: str, reviewer: int) -> int:
    digest = hashlib.sha256(f"{target_period}|{phase}|{reviewer}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _anonymized_items(
    items: list[dict[str, Any]],
    *,
    target_period: str,
    phase: str,
    reviewer: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    indices = list(range(len(items)))
    random.Random(_seed(target_period, phase, reviewer)).shuffle(indices)
    mapping: dict[str, int] = {}
    payload: list[dict[str, Any]] = []
    for label, index in zip(_LABELS, indices, strict=True):
        mapping[label] = index
        value = dict(items[index])
        value.pop("position", None)
        value.pop("number", None)
        payload.append({"candidate_id": label, "evidence": value})
    return payload, mapping


_NEUTRAL_IDS = tuple(f"N{index:02d}" for index in range(1, 11))


def _shared_anonymized_items(
    items: list[dict[str, Any]],
    *,
    target_period: str,
    phase: str,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[int, str]]:
    """Build one neutral evidence namespace shared by all reviewers in a phase."""
    _, shared_order = _anonymized_items(
        items,
        target_period=target_period,
        phase=phase,
        reviewer=0,
    )
    neutral_mapping: dict[str, int] = {}
    payload: list[dict[str, Any]] = []
    for neutral_id, actual_index in zip(
        _NEUTRAL_IDS,
        shared_order.values(),
        strict=True,
    ):
        neutral_mapping[neutral_id] = actual_index
        value = dict(items[actual_index])
        value.pop("position", None)
        value.pop("number", None)
        payload.append({"evidence_id": neutral_id, "evidence": value})
    neutral_by_actual = {
        actual_index: neutral_id
        for neutral_id, actual_index in neutral_mapping.items()
    }
    return payload, neutral_mapping, neutral_by_actual


def _reviewer_aliases(
    reviewer_mapping: dict[str, int],
    neutral_by_actual: dict[int, str],
) -> dict[str, str]:
    return {
        label: neutral_by_actual[actual_index]
        for label, actual_index in reviewer_mapping.items()
    }


def _anonymized_position_history(
    history: list[DrawModel],
    mapping: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        {
            "period": draw.period,
            "values_by_candidate": {
                label: draw.numbers[position]
                for label, position in mapping.items()
            },
        }
        for draw in _canonical_history(history)
    ]


def _anonymized_number_series(
    history: list[DrawModel],
    position: int,
    mapping: dict[str, int],
    *,
    mask_recent: int = 0,
) -> list[dict[str, str]]:
    scoped = _history_scope(history, mask_recent=mask_recent)
    label_by_number = {
        actual_index + 1: label for label, actual_index in mapping.items()
    }
    return [
        {
            "period": draw.period,
            "candidate_id": label_by_number[draw.numbers[position]],
        }
        for draw in scoped
    ]


def _parse_label_scores(
    result: dict[str, Any],
    mapping: dict[str, int],
) -> _ReviewerResult:
    raw_scores = result.get("scores")
    if not isinstance(raw_scores, dict):
        raise ValueError("AI 必须返回10个匿名候选评分")
    scores = [0.0] * 10
    for label, actual_index in mapping.items():
        raw = raw_scores.get(label)
        if raw is None:
            raise ValueError(f"AI 缺少候选{label}评分")
        value = float(raw)
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"AI 候选{label}评分无效")
        scores[actual_index] = value
    raw_usage = result.get("_tianji_usage")
    usage = raw_usage if isinstance(raw_usage, dict) else {}
    return _ReviewerResult(
        scores=_normalize(scores),
        analysis=str(result.get("analysis") or "").strip()[:300],
        usage={str(key): max(0, int(value)) for key, value in usage.items()},
    )


def _position_review(
    config: RuntimeAiConfig,
    *,
    history: list[DrawModel],
    evidence: list[dict[str, Any]],
    target_period: str,
    trained_through_period: str,
    reviewer: int,
    challenge: bool,
) -> _ReviewerResult:
    shared_candidates, neutral_mapping, neutral_by_actual = _shared_anonymized_items(
        evidence,
        target_period=target_period,
        phase="position-shared",
    )
    # Preserve the exact reviewer-specific permutation seed used before caching.
    _, reviewer_mapping = _anonymized_items(
        evidence,
        target_period=target_period,
        phase="position-challenge" if challenge else "position",
        reviewer=reviewer,
    )
    prompt = (
        "你是天机服务端的独立前向预测评审。共享证据中的N01至N10是服务器随机生成的中性编号，"
        "不会暴露真实名次；本路参数会单独给出A至J到这些中性编号的一次性映射。"
        "必须按照本路映射独立分析，不得猜测真实名次，也不得参考其他评审。"
        "你会看到完整匿名开奖序列和程序逐期核验的统计证据，需对A至J全部给出0以上评分。"
        "评分代表相对预测证据，不是真实中奖概率；必须明确选出证据最高的一个候选。"
        "只返回紧凑JSON：{\"scores\":{\"A\":数值,...,\"J\":数值},"
        "\"selected\":\"A至J之一\",\"analysis\":\"不超过120字简体中文\"}。"
    )
    result = _call_json(
        config,
        system_prompt=prompt,
        shared_payload={
            "target_period": target_period,
            "trained_through_period": trained_through_period,
            "history_order": "oldest_to_newest",
            "evidence_mode": "neutral_anonymous_full_sequence_plus_aggregates",
            "neutral_raw_draws": _anonymized_position_history(
                history,
                neutral_mapping,
            ),
            "neutral_candidates": shared_candidates,
        },
        reviewer_payload={
            "reviewer": reviewer + 1,
            "independent_review": True,
            "candidate_aliases_A_to_J": _reviewer_aliases(
                reviewer_mapping,
                neutral_by_actual,
            ),
            "challenge": challenge,
            "review_instruction": (
                "最近正式结果出现同一名次连续入选。本轮主动复核首位偏置、惯性选择和弱证据；"
                "若匿名证据仍支持同一候选可以继续选择，禁止为了轮换故意换名次。"
                if challenge
                else "基于共享中性匿名证据独立评分，不参考其他评审结果。"
            ),
        },
        max_tokens=1200,
        timeout_seconds=55,
    )
    return _parse_label_scores(result, reviewer_mapping)


def _number_evidence(
    history: list[DrawModel],
    position: int,
    *,
    mask_recent: int = 0,
) -> list[dict[str, Any]]:
    scoped = _history_scope(history, mask_recent=mask_recent)
    values = [draw.numbers[position] for draw in scoped]
    count12 = _counts(values, 12)
    count30 = _counts(values, 30)
    count60 = _counts(values, 60)
    count120 = _counts(values, 120)
    omission = _omission(values)
    current = values[-1]
    successors = [0] * 10
    transition_samples = 0
    for index in range(1, len(values)):
        if values[index - 1] == current:
            successors[values[index] - 1] += 1
            transition_samples += 1

    short_size = min(12, len(values))
    medium_size = min(30, len(values))
    long_size = min(60, len(values))
    full_size = len(values)
    return [
        {
            "number": number,
            "count_12": count12[number - 1],
            "count_30": count30[number - 1],
            "count_60": count60[number - 1],
            "count_120": count120[number - 1],
            "omission": omission[number - 1],
            "successor_after_current": successors[number - 1],
            "successor_sample_size": transition_samples,
            "short_rate": round(count12[number - 1] / short_size, 6),
            "medium_rate": round(count30[number - 1] / medium_size, 6),
            "long_rate": round(count60[number - 1] / long_size, 6),
            "full_rate": round(count120[number - 1] / full_size, 6),
            "short_vs_medium_delta": round(
                count12[number - 1] / short_size
                - count30[number - 1] / medium_size,
                6,
            ),
            "medium_vs_long_delta": round(
                count30[number - 1] / medium_size
                - count60[number - 1] / long_size,
                6,
            ),
            "transition_rate": (
                round(successors[number - 1] / transition_samples, 6)
                if transition_samples
                else 0.0
            ),
        }
        for number in range(1, 11)
    ]


def _number_review(
    config: RuntimeAiConfig,
    *,
    history: list[DrawModel],
    position: int,
    target_period: str,
    trained_through_period: str,
    reviewer: int,
    mask_recent: int = 0,
) -> _ReviewerResult:
    evidence = _number_evidence(
        history,
        position,
        mask_recent=mask_recent,
    )
    phase = f"number-{position}-masked-{mask_recent}"
    shared_candidates, neutral_mapping, neutral_by_actual = _shared_anonymized_items(
        evidence,
        target_period=target_period,
        phase=f"{phase}-shared",
    )
    # Preserve the exact per-reviewer A-J permutation from the original algorithm.
    _, reviewer_mapping = _anonymized_items(
        evidence,
        target_period=target_period,
        phase=phase,
        reviewer=reviewer,
    )
    neutral_history = _anonymized_number_series(
        history,
        position,
        neutral_mapping,
        mask_recent=mask_recent,
    )
    prompt = (
        "你是天机服务端的独立号码排序评审。共享证据中的N01至N10是服务器随机生成的中性编号，"
        "不会暴露真实号码；本路参数会给出A至J到这些中性编号的一次性随机映射。"
        "必须按照本路映射独立评分，不得猜测真实号码身份，不得参考其他评审。"
        "请依据完整匿名历史时序、短中长期频率、遗漏、转移和趋势证据，分析先后顺序、"
        "重复间隔、冷热切换、状态转移与多窗口稳定性，而不是只抄最近出现过的集合。"
        + (
            "本轮为近期集合复刻复核，最近7期已作为留出窗口隐藏；仅依据更早时序评分。"
            if mask_recent
            else "本轮使用开奖前可见的完整匿名历史时序进行首次独立评分。"
        )
        + "每期必须给出完整排序。只返回紧凑JSON："
        "{\"scores\":{\"A\":数值,...,\"J\":数值},"
        "\"selected\":\"A至J之一\",\"analysis\":\"不超过100字简体中文\"}。"
    )
    result = _call_json(
        config,
        system_prompt=prompt,
        shared_payload={
            "target_period": target_period,
            "trained_through_period": trained_through_period,
            "selected_position": position + 1,
            "history_order": "oldest_to_newest",
            "masked_recent_draws": mask_recent,
            "evidence_mode": "neutral_anonymous_full_sequence_plus_aggregates",
            "neutral_history": neutral_history,
            "neutral_candidates": shared_candidates,
        },
        reviewer_payload={
            "reviewer": reviewer + 1,
            "independent_review": True,
            "candidate_aliases_A_to_J": _reviewer_aliases(
                reviewer_mapping,
                neutral_by_actual,
            ),
            "review_instruction": "仅依据共享中性匿名证据独立评分，不参考其他评审结果。",
        },
        max_tokens=1400,
        timeout_seconds=50,
    )
    return _parse_label_scores(result, reviewer_mapping)


def _run_parallel(count: int, task: Any) -> list[_ReviewerResult]:
    results: list[_ReviewerResult] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=count, thread_name_prefix="tianji-ai-review") as pool:
        futures = [pool.submit(task, reviewer) for reviewer in range(count)]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc)[:180])
    if not results:
        raise RuntimeError("全部AI评审失败：" + "；".join(errors[:3]))
    return results


def _run_prefix_cached(count: int, task: Any) -> list[_ReviewerResult]:
    """Complete one real review first, then run the rest while preserving IDs."""
    indexed: dict[int, _ReviewerResult] = {}
    errors: list[str] = []
    warm_count = min(1, max(0, count))
    for reviewer in range(warm_count):
        try:
            indexed[reviewer] = task(reviewer)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc)[:180])
    remaining = list(range(warm_count, count))
    if remaining:
        with ThreadPoolExecutor(
            max_workers=len(remaining),
            thread_name_prefix="tianji-ai-cache-hit",
        ) as pool:
            futures = {pool.submit(task, reviewer): reviewer for reviewer in remaining}
            for future in as_completed(futures):
                reviewer = futures[future]
                try:
                    indexed[reviewer] = future.result()
                except Exception as exc:  # noqa: BLE001
                    errors.append(str(exc)[:180])
    if not indexed:
        raise RuntimeError("全部AI评审失败：" + "；".join(errors[:3]))
    return [indexed[index] for index in sorted(indexed)]


def _aggregate(results: list[_ReviewerResult]) -> list[float]:
    size = len(results[0].scores)
    return _normalize(
        [
            sum(result.scores[index] for result in results) / len(results)
            for index in range(size)
        ]
    )


def _blend_probabilities(
    primary: list[float],
    holdout: list[float],
    *,
    holdout_weight: float = _HOLDOUT_REVIEW_WEIGHT,
) -> list[float]:
    safe_weight = max(0.0, min(1.0, holdout_weight))
    return _normalize(
        [
            primary[index] * (1.0 - safe_weight)
            + holdout[index] * safe_weight
            for index in range(len(primary))
        ]
    )


def needs_collapse_review(recent_positions: list[int], selected_position: int) -> bool:
    streak = 0
    for position in recent_positions:
        if position != selected_position:
            break
        streak += 1
    return streak >= 3


def _recent_window_set(
    history: list[DrawModel],
    position: int,
    window: int = _RECENT_COPY_WINDOW,
) -> set[int]:
    verified = _canonical_history(history)
    return {draw.numbers[position] for draw in verified[-window:]}


def _matches_recent_window(
    ranked: list[int],
    history: list[DrawModel],
    position: int,
    window: int = _RECENT_COPY_WINDOW,
) -> bool:
    del window
    return recent_copy_diagnostics(ranked, history, position).triggered


def analyze_ensemble(
    history: list[DrawModel],
    target_period: str,
    config: RuntimeAiConfig,
    *,
    recent_positions: list[int] | None = None,
    strategy_weights: dict[str, float] | None = None,
) -> AiEnsembleResult:
    if not config.complete:
        raise RuntimeError("服务器尚未完整配置AI")
    verified = _canonical_history(history)
    if len(verified) < 30:
        raise ValueError("AI预测至少需要30期有效历史")
    trained_through = verified[-1].period
    started = time.monotonic()
    evidence = build_position_evidence(verified)

    # AI source is intentionally independent: no native statistical component
    # participates in position selection or number ranking.
    position_results = _run_prefix_cached(
        _POSITION_REVIEWERS,
        lambda reviewer: _position_review(
            config,
            history=verified,
            evidence=evidence,
            target_period=target_period,
            trained_through_period=trained_through,
            reviewer=reviewer,
            challenge=False,
        ),
    )
    position_scores = _aggregate(position_results)
    selected_position = max(range(10), key=position_scores.__getitem__)
    recent = recent_positions or []
    collapse_reviewed = needs_collapse_review(recent, selected_position)
    if collapse_reviewed:
        challenge_results = _run_prefix_cached(
            2,
            lambda reviewer: _position_review(
                config,
                history=verified,
                evidence=evidence,
                target_period=target_period,
                trained_through_period=trained_through,
                reviewer=reviewer + 100,
                challenge=True,
            ),
        )
        position_results.extend(challenge_results)
        position_scores = _aggregate(position_results)
        selected_position = max(range(10), key=position_scores.__getitem__)

    number_results = _run_prefix_cached(
        _NUMBER_REVIEWERS,
        lambda reviewer: _number_review(
            config,
            history=verified,
            position=selected_position,
            target_period=target_period,
            trained_through_period=trained_through,
            reviewer=reviewer,
            mask_recent=0,
        ),
    )
    strategy_probabilities = {
        f"ai_reviewer_{index + 1}": _normalize(result.scores)
        for index, result in enumerate(number_results)
    }
    active_strategy_weights = normalize_strategy_weights(
        strategy_weights,
        strategy_probabilities,
    )
    probabilities = blend_strategy_probabilities(
        strategy_probabilities,
        active_strategy_weights,
    )
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)

    raw_copy = recent_copy_diagnostics(ranked, verified, selected_position)
    ai_score_spread = max(probabilities) - min(probabilities)
    final_boundary = probabilities[ranked[5]] - probabilities[ranked[6]]
    recent_copy_reviewed = (
        raw_copy.exact_latest_six
        or (raw_copy.triggered and ai_score_spread >= 0.02 and final_boundary >= 0.004)
    )
    holdout_results: list[_ReviewerResult] = []
    if recent_copy_reviewed:
        holdout_results = _run_prefix_cached(
            _NUMBER_REVIEWERS,
            lambda reviewer: _number_review(
                config,
                history=verified,
                position=selected_position,
                target_period=target_period,
                trained_through_period=trained_through,
                reviewer=reviewer + 100,
                mask_recent=_RECENT_COPY_WINDOW,
            ),
        )
        number_results.extend(holdout_results)
        for index, result in enumerate(holdout_results):
            strategy_probabilities[f"ai_holdout_{index + 1}"] = _normalize(result.scores)
        learned = dict(strategy_weights or {})
        if not any(name.startswith("ai_holdout_") for name in learned):
            for name in strategy_probabilities:
                learned.setdefault(name, 0.35 if name.startswith("ai_holdout_") else 0.15)
        active_strategy_weights = normalize_strategy_weights(
            learned,
            strategy_probabilities,
        )
        probabilities = blend_strategy_probabilities(
            strategy_probabilities,
            active_strategy_weights,
        )
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)

    position_margin = sorted(position_scores, reverse=True)
    margin = (
        (position_margin[0] - position_margin[1]) * 100
        if len(position_margin) > 1
        else 0.0
    )
    position_comment = next((item.analysis for item in position_results if item.analysis), "")
    number_comment_source = holdout_results or number_results
    number_comment = next((item.analysis for item in number_comment_source if item.analysis), "")
    analysis = (
        f"{len(position_results)}轮独立AI匿名名次评审选择第{selected_position + 1}名，"
        f"前两名次AI评分差约{margin:.2f}个百分点；"
        f"{len(number_results)}轮独立AI匿名时序评审完成号码排序。"
        + (f" {position_comment}" if position_comment else "")
        + (f" {number_comment}" if number_comment else "")
        + " AI预测不再混入本地频率、遗漏、马尔可夫、趋势或稳定性策略。"
    )[:520]
    if collapse_reviewed:
        analysis = (analysis + " 已触发连续同名次的额外AI挑战评审。")[:580]
    if recent_copy_reviewed:
        analysis = (
            analysis + " 初次结果与最近集合高度重合，已增加隐藏最近7期的独立AI留出评审，避免直接复制最新六码。"
        )[:640]
    learning_leaders = sorted(
        active_strategy_weights.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    learning_text = "、".join(
        f"{name} {weight * 100:.1f}%" for name, weight in learning_leaders
    )
    analysis = (
        analysis
        + f" AI评审权重按最近100期50%、最近300期30%、全历史20%独立学习：{learning_text}。"
    )[:760]

    usage = _merge_usage([*position_results, *number_results])
    cache_input_tokens = usage["prompt_cache_hit_tokens"] + usage["prompt_cache_miss_tokens"]
    cache_hit_rate = (
        usage["prompt_cache_hit_tokens"] / cache_input_tokens
        if cache_input_tokens
        else 0.0
    )

    return AiEnsembleResult(
        position=selected_position,
        probabilities=probabilities,
        top6=[index + 1 for index in ranked[:6]],
        top7=[index + 1 for index in ranked[:7]],
        analysis=analysis,
        risk_note=(
            "这是开奖前冻结的独立AI多路匿名排序，保留完整历史先后顺序。AI只读取匿名历史与证据，不再复用本地模型最终概率；"
            "本地数学模型与AI模型分别结算、分别学习。随机开奖仍可能使任何分析失效。"
        ),
        latency_ms=int((time.monotonic() - started) * 1000),
        position_reviewers=len(position_results),
        number_reviewers=len(number_results),
        collapse_reviewed=collapse_reviewed,
        recent_copy_reviewed=recent_copy_reviewed,
        request_count=usage["request_count"],
        prompt_tokens=usage["prompt_tokens"],
        prompt_cache_hit_tokens=usage["prompt_cache_hit_tokens"],
        prompt_cache_miss_tokens=usage["prompt_cache_miss_tokens"],
        completion_tokens=usage["completion_tokens"],
        reasoning_tokens=usage["reasoning_tokens"],
        cache_hit_rate=round(cache_hit_rate, 6),
        strategy_probabilities=strategy_probabilities,
        strategy_weights=active_strategy_weights,
    )
