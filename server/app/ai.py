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
    request_count: int = 0
    prompt_tokens: int = 0
    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    cache_hit_rate: float = 0.0


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


def _contains_chinese(value: str) -> bool:
    return any("\u3400" <= char <= "\u9fff" for char in value)


def _chinese_text(value: Any, fallback: str, limit: int) -> str:
    text = str(value or "").strip()
    if not text or not _contains_chinese(text):
        return fallback
    return text[:limit]


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
    return ""


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


def _is_official_deepseek(config: RuntimeAiConfig) -> bool:
    endpoint = config.endpoint.lower()
    return "api.deepseek.com" in endpoint and config.model.lower().startswith("deepseek-")


def _deepseek_fast_mode(body: dict[str, Any], *, max_tokens: int) -> dict[str, Any]:
    """DeepSeek V4 默认开启思考；短测试和限时 JSON 任务显式关闭思考。"""
    result = dict(body)
    result["thinking"] = {"type": "disabled"}
    result["max_tokens"] = max_tokens
    result.pop("reasoning_effort", None)
    return result


def _post_json(
    client: httpx.Client,
    *,
    endpoint: str,
    headers: dict[str, str],
    body: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(endpoint, headers=headers, json=body)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("AI 接口返回格式异常")
    return payload


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
    """真实调用当前模型，并确保能返回最终正文。"""
    active = config or load_ai_config()
    if not active.complete:
        raise RuntimeError("请先完整配置 HTTPS 接口、模型和 API Key")

    models: list[str] = []
    models_note = "模型列表未读取"
    try:
        discovered = discover_models(active)
        models = discovered.models
        models_note = f"读取到 {len(models)} 个模型"
    except Exception as exc:
        models_note = f"模型列表读取失败：{str(exc)[:100]}"

    is_responses = active.endpoint.rstrip("/").endswith("/responses")
    if is_responses:
        body: dict[str, Any] = {
            "model": active.model,
            "input": "只回复：OK",
            "max_output_tokens": 64,
        }
    else:
        body = {
            "model": active.model,
            "messages": [{"role": "user", "content": "只回复：OK"}],
            "temperature": 0,
            "stream": False,
            "max_tokens": 64,
        }
        if _is_official_deepseek(active):
            body = _deepseek_fast_mode(body, max_tokens=64)

    started = time.monotonic()
    with httpx.Client(
        timeout=httpx.Timeout(min(active.timeout_seconds, 60), connect=10.0),
        follow_redirects=True,
    ) as client:
        payload = _post_json(
            client,
            endpoint=active.endpoint,
            headers=_headers(active),
            body=body,
        )
        text = _response_text(payload).strip()
        if not text and not is_responses:
            retry_body = dict(body)
            retry_body["max_tokens"] = 256
            if _is_official_deepseek(active):
                retry_body = _deepseek_fast_mode(retry_body, max_tokens=256)
            payload = _post_json(
                client,
                endpoint=active.endpoint,
                headers=_headers(active),
                body=retry_body,
            )
            text = _response_text(payload).strip()
    if not text:
        raise ValueError("模型接口已响应，但最终回答为空；系统已关闭思考模式并自动重试，仍未获得正文")
    latency_ms = int((time.monotonic() - started) * 1000)
    return AiConnectionResult(
        latency_ms=latency_ms,
        message=f"模型 {active.model} 调用成功，{models_note}",
        models=models or [active.model],
    )


def analyze(
    history: list[DrawModel],
    target_period: str,
    config: RuntimeAiConfig | None = None,
    *,
    recent_positions: list[int] | None = None,
) -> AiPrediction:
    """Generate an AI-only forward prediction through anonymous multi-review consensus."""
    from .ai_ensemble import analyze_ensemble

    active = config or load_ai_config()
    result = analyze_ensemble(
        history,
        target_period,
        active,
        recent_positions=recent_positions,
    )
    return AiPrediction(
        position=result.position,
        probabilities=result.probabilities,
        top6=result.top6,
        top7=result.top7,
        analysis=result.analysis,
        risk_note=result.risk_note,
        model=active.model,
        latency_ms=result.latency_ms,
        request_count=result.request_count,
        prompt_tokens=result.prompt_tokens,
        prompt_cache_hit_tokens=result.prompt_cache_hit_tokens,
        prompt_cache_miss_tokens=result.prompt_cache_miss_tokens,
        completion_tokens=result.completion_tokens,
        reasoning_tokens=result.reasoning_tokens,
        cache_hit_rate=result.cache_hit_rate,
    )
