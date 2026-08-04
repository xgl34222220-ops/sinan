from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time
from typing import Any

import httpx

from .models import DrawModel, compact_json
from .runtime_config import RuntimeAiConfig, load_ai_config


@dataclass(frozen=True)
class AiPrediction:
    position: int
    probabilities: list[float]
    top6: list[int]
    top7: list[int]
    analysis: str
    risk_note: str
    model: str
    latency_ms: int


@dataclass(frozen=True)
class AiConnectionResult:
    latency_ms: int
    message: str
    models: list[str]


def _normalize(scores: list[float]) -> list[float]:
    safe = [value if value >= 0 and value == value else 0.0 for value in scores]
    total = sum(safe)
    if total <= 0:
        raise ValueError("AI 返回的评分全部为零")
    return [value / total for value in safe]


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
    raise ValueError("AI 没有返回有效 JSON")


def _response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
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
                    parts.append(part["text"])
        if parts:
            return "\n".join(parts)
    raise ValueError("AI 接口没有返回正文")


def _headers(config: RuntimeAiConfig) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _models_endpoint(endpoint: str) -> str:
    value = endpoint.rstrip("/")
    for suffix in ("/chat/completions", "/responses"):
        if value.endswith(suffix):
            return value[: -len(suffix)] + "/models"
    if value.endswith("/v1"):
        return value + "/models"
    return value + "/models"


def discover_models(config: RuntimeAiConfig | None = None) -> AiConnectionResult:
    active = config or load_ai_config()
    if not active.complete:
        raise RuntimeError("请先完整配置 HTTPS 接口、模型和 API Key")
    started = time.monotonic()
    endpoint = _models_endpoint(active.endpoint)
    with httpx.Client(
        timeout=httpx.Timeout(min(active.timeout_seconds, 30), connect=10.0),
        follow_redirects=True,
    ) as client:
        response = client.get(endpoint, headers=_headers(active))
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("模型接口返回格式异常")
    data = payload.get("data")
    models: list[str] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                model_id = str(item.get("id") or "").strip()
                if model_id:
                    models.append(model_id)
    models = sorted(set(models))
    latency_ms = int((time.monotonic() - started) * 1000)
    return AiConnectionResult(
        latency_ms=latency_ms,
        message=f"连接正常，读取到 {len(models)} 个模型" if models else "连接正常，但接口未返回模型列表",
        models=models,
    )


def test_connection(config: RuntimeAiConfig | None = None) -> AiConnectionResult:
    active = config or load_ai_config()
    try:
        return discover_models(active)
    except Exception as model_error:
        if not active.complete:
            raise
        is_responses = active.endpoint.rstrip("/").endswith("/responses")
        if is_responses:
            body: dict[str, Any] = {
                "model": active.model,
                "input": "只回复：OK",
                "max_output_tokens": 8,
            }
        else:
            body = {
                "model": active.model,
                "messages": [{"role": "user", "content": "只回复：OK"}],
                "temperature": 0,
                "stream": False,
                "max_tokens": 8,
            }
        started = time.monotonic()
        with httpx.Client(
            timeout=httpx.Timeout(min(active.timeout_seconds, 45), connect=10.0),
            follow_redirects=True,
        ) as client:
            response = client.post(active.endpoint, headers=_headers(active), json=body)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("AI 接口返回格式异常")
        _response_text(payload)
        latency_ms = int((time.monotonic() - started) * 1000)
        return AiConnectionResult(
            latency_ms=latency_ms,
            message=f"模型调用成功；模型列表读取失败：{str(model_error)[:120]}",
            models=[active.model],
        )


def analyze(
    history: list[DrawModel],
    target_period: str,
    config: RuntimeAiConfig | None = None,
) -> AiPrediction:
    active = config or load_ai_config()
    if not active.complete:
        raise RuntimeError("服务器尚未完整配置 AI")
    verified = [draw for draw in history if len(draw.numbers) == 10][-120:]
    if len(verified) < 30:
        raise ValueError("AI 分析至少需要 30 期有效历史")

    history_payload = [
        {"period": draw.period, "numbers": draw.numbers, "draw_time": draw.draw_time}
        for draw in verified
    ]
    system_prompt = (
        "你是天机的独立概率排序模型。只能依据提供的真实开奖历史进行统计比较，"
        "不得承诺必中、盈利或准确率，不得输出隐藏思维链。"
        "比较十个名次后选择证据相对更充分的一名，按号码1至10顺序给出10项非负评分。"
        "只返回紧凑JSON：{\"position\":1至10整数,\"scores\":[10项非负数],"
        "\"analysis\":\"不超过100字\",\"risk_note\":\"不超过80字\"}。"
    )
    user_prompt = compact_json(
        {
            "target_period": target_period,
            "trained_through_period": verified[-1].period,
            "history_count": len(verified),
            "history": history_payload,
        }
    )
    endpoint = active.endpoint
    is_responses = endpoint.rstrip("/").endswith("/responses")
    if is_responses:
        body: dict[str, Any] = {
            "model": active.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
    else:
        body = {
            "model": active.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.15,
            "stream": False,
            "response_format": {"type": "json_object"},
        }

    started = time.monotonic()
    with httpx.Client(
        timeout=httpx.Timeout(active.timeout_seconds, connect=15.0),
        follow_redirects=True,
    ) as client:
        response = client.post(endpoint, headers=_headers(active), json=body)
        if response.status_code >= 400 and not is_responses and "response_format" in body:
            body.pop("response_format", None)
            response = client.post(endpoint, headers=_headers(active), json=body)
        response.raise_for_status()
        payload = response.json()
    latency_ms = int((time.monotonic() - started) * 1000)
    if not isinstance(payload, dict):
        raise ValueError("AI 返回格式异常")
    result = _extract_json(_response_text(payload))
    position = int(result.get("position", 0)) - 1
    if position not in range(10):
        raise ValueError("AI 返回的名次无效")
    raw_scores = result.get("scores")
    if not isinstance(raw_scores, list) or len(raw_scores) != 10:
        raise ValueError("AI 必须返回号码1至10的10项评分")
    scores = [float(value) for value in raw_scores]
    probabilities = _normalize(scores)
    ranked = sorted(range(10), key=lambda index: probabilities[index], reverse=True)
    analysis_text = str(result.get("analysis", "AI 已完成独立统计比较"))[:240]
    risk_text = str(
        result.get("risk_note", "随机开奖不可可靠预测，结果仅用于前向验证")
    )[:200]
    return AiPrediction(
        position=position,
        probabilities=probabilities,
        top6=[index + 1 for index in ranked[:6]],
        top7=[index + 1 for index in ranked[:7]],
        analysis=analysis_text,
        risk_note=risk_text,
        model=active.model,
        latency_ms=latency_ms,
    )
