from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import json
import math
import random
import re
import time
from typing import Any

import httpx

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


@dataclass(frozen=True)
class _ReviewerResult:
    scores: list[float]
    analysis: str


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
    user_payload: dict[str, Any],
    max_tokens: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    endpoint = config.endpoint.rstrip("/")
    is_responses = endpoint.endswith("/responses")
    if is_responses:
        body: dict[str, Any] = {
            "model": config.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_json(user_payload)},
            ],
            "max_output_tokens": max_tokens,
        }
    else:
        body = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_json(user_payload)},
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
            text = _response_text(payload).strip()
            if not text:
                raise ValueError("AI 最终正文为空")
            return _extract_json(text)
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
    return _ReviewerResult(
        scores=_normalize(scores),
        analysis=str(result.get("analysis") or "").strip()[:300],
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
    candidates, mapping = _anonymized_items(
        evidence,
        target_period=target_period,
        phase="position-challenge" if challenge else "position",
        reviewer=reviewer,
    )
    prompt = (
        "你是天机服务端的独立前向预测评审。候选A至J对应十个真实名次，但映射已随机匿名，"
        "不得猜测字母对应哪个名次，也不得偏向列表第一项。你会同时看到匿名后的原始开奖序列和程序逐期核验的统计证据，"
        "对全部10个候选给出0以上评分。评分代表相对预测证据，不是真实中奖概率。"
        "必须明确选出证据最高的一个候选，每期必须形成预测，不得回答无法预测。"
        + (
            "最近正式结果出现同一名次连续入选，本轮是反偏置复核。请主动寻找首位偏置、惯性选择和弱证据，"
            "但如果匿名证据仍支持同一候选，也可以继续选择，禁止为了轮换而故意换名次。"
            if challenge
            else ""
        )
        + "只返回紧凑JSON：{\"scores\":{\"A\":数值,...,\"J\":数值},"
        "\"selected\":\"A至J之一\",\"analysis\":\"不超过120字简体中文\"}。"
    )
    result = _call_json(
        config,
        system_prompt=prompt,
        user_payload={
            "target_period": target_period,
            "trained_through_period": trained_through_period,
            "reviewer": reviewer + 1,
            "history_order": "oldest_to_newest",
            "anonymous_raw_draws": _anonymized_position_history(history, mapping),
            "candidates": candidates,
        },
        max_tokens=1200,
        timeout_seconds=55,
    )
    return _parse_label_scores(result, mapping)


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
    candidates, mapping = _anonymized_items(
        evidence,
        target_period=target_period,
        phase=phase,
        reviewer=reviewer,
    )
    anonymous_history = _anonymized_number_series(
        history,
        position,
        mapping,
        mask_recent=mask_recent,
    )
    prompt = (
        "你是天机服务端的独立号码排序评审。候选A至J对应号码1至10，但每轮映射都会随机改变并由服务端保密。"
        "你会看到该名次完整的匿名历史时间序列，以及使用同一匿名映射生成的短中长期频率、遗漏、转移和趋势证据。"
        "请分析真实的先后顺序、重复间隔、冷热切换、状态转移与多窗口稳定性，而不是只抄最近出现过的候选集合。"
        "任何输入都不会暴露A至J对应的真实号码；不得猜测真实号码身份，不得偏向列表第一项，不得编造统计。"
        + (
            "本轮为近期集合复刻复核，最近7期已作为留出窗口隐藏；请仅依据更早的完整匿名时序独立评分。"
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
        user_payload={
            "target_period": target_period,
            "trained_through_period": trained_through_period,
            "selected_position": position + 1,
            "reviewer": reviewer + 1,
            "history_order": "oldest_to_newest",
            "masked_recent_draws": mask_recent,
            "evidence_mode": "anonymous_full_sequence_plus_aggregates",
            "anonymous_history": anonymous_history,
            "candidates": candidates,
        },
        max_tokens=1400,
        timeout_seconds=50,
    )
    return _parse_label_scores(result, mapping)


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
    return streak >= 6


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
    recent = _recent_window_set(history, position, window)
    predicted = {index + 1 for index in ranked[:window]}
    return len(recent) >= window - 1 and recent.issubset(predicted)


def analyze_ensemble(
    history: list[DrawModel],
    target_period: str,
    config: RuntimeAiConfig,
    *,
    recent_positions: list[int] | None = None,
) -> AiEnsembleResult:
    if not config.complete:
        raise RuntimeError("服务器尚未完整配置AI")
    verified = _canonical_history(history)
    if len(verified) < 30:
        raise ValueError("AI预测至少需要30期有效历史")
    trained_through = verified[-1].period
    started = time.monotonic()
    evidence = build_position_evidence(verified)

    position_results = _run_parallel(
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

    collapse_reviewed = needs_collapse_review(
        recent_positions or [],
        selected_position,
    )
    if collapse_reviewed:
        challenge_results = _run_parallel(
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

    number_results = _run_parallel(
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
    primary_probabilities = _aggregate(number_results)
    probabilities = primary_probabilities
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)

    recent_copy_reviewed = _matches_recent_window(
        ranked,
        verified,
        selected_position,
    )
    holdout_results: list[_ReviewerResult] = []
    if recent_copy_reviewed:
        holdout_results = _run_parallel(
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
        holdout_probabilities = _aggregate(holdout_results)
        probabilities = _blend_probabilities(
            primary_probabilities,
            holdout_probabilities,
        )
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)

    position_margin = sorted(position_scores, reverse=True)
    margin = (
        (position_margin[0] - position_margin[1]) * 100
        if len(position_margin) > 1
        else 0.0
    )
    position_comment = next(
        (item.analysis for item in position_results if item.analysis),
        "",
    )
    number_comment_source = holdout_results or number_results
    number_comment = next(
        (item.analysis for item in number_comment_source if item.analysis),
        "",
    )
    analysis = (
        f"{len(position_results)}轮匿名名次评审选择第{selected_position + 1}名，"
        f"前两名次汇总差约{margin:.2f}个百分点；"
        f"{len(number_results)}轮完整匿名时序号码评审完成独立排序。"
        + (f" {position_comment}" if position_comment else "")
        + (f" {number_comment}" if number_comment else "")
    )[:380]
    if collapse_reviewed:
        analysis = (
            analysis + " 已触发连续同名次反偏置复核，未人为强制轮换。"
        )[:440]
    if recent_copy_reviewed:
        analysis = (
            analysis
            + " 初次Top 7与最近7期候选集合高度重合，已增加隐藏最近7期的独立留出评审；最终结果由完整历史评审与留出评审加权汇总，并非程序换号。"
        )[:560]

    return AiEnsembleResult(
        position=selected_position,
        probabilities=probabilities,
        top6=[index + 1 for index in ranked[:6]],
        top7=[index + 1 for index in ranked[:7]],
        analysis=analysis,
        risk_note=(
            "这是开奖前冻结的AI多轮相对排序。号码阶段保留完整历史先后顺序，但每轮都将号码随机映射为A至J，"
            "模型只能看到匿名时序与同映射聚合证据；检测到近期集合复刻时会增加留出窗口复核。"
            "随机开奖仍可能使任何分析失效，只能用于前向验证。"
        ),
        latency_ms=int((time.monotonic() - started) * 1000),
        position_reviewers=len(position_results),
        number_reviewers=len(number_results),
        collapse_reviewed=collapse_reviewed,
        recent_copy_reviewed=recent_copy_reviewed,
    )
