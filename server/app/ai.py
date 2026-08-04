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
        "analysis 与 risk_note 必须使用自然、易懂的简体中文完整句子，禁止输出英文句子、拼音或中英混排；"
        "模型名称和必要技术缩写除外。"
        "只返回紧凑JSON：{\"position\":1至10整数,\"scores\":[10项非负数],"
        "\"analysis\":\"不超过100字的简体中文分析\",\"risk_note\":\"不超过80字的简体中文风险提示\"}。"
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
            "max_tokens": 900,
        }
        if _is_official_deepseek(active):
            body = _deepseek_fast_mode(body, max_tokens=900)

    started = time.monotonic()
    with httpx.Client(
        timeout=httpx.Timeout(active.timeout_seconds, connect=15.0),
        follow_redirects=True,
    ) as client:
        response = client.post(endpoint, headers=_headers(active), json=body)
        if response.status_code >= 400 and not is_responses and "response_format" in body:
            retry_body = dict(body)
            retry_body.pop("response_format", None)
            response = client.post(endpoint, headers=_headers(active), json=retry_body)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("AI 返回格式异常")
        text = _response_text(payload).strip()

        # DeepSeek 官方说明 JSON Output 偶尔可能返回空正文。
        # 空正文时自动去掉 response_format 再请求一次，仍要求只输出 JSON。
        if not text and not is_responses:
            retry_body = dict(body)
            retry_body.pop("response_format", None)
            retry_messages = list(retry_body.get("messages") or [])
            retry_messages.append(
                {
                    "role": "user",
                    "content": "上一次返回为空。请立即只返回一行完整 JSON，analysis 和 risk_note 必须是简体中文，不要解释，不要留空。",
                }
            )
            retry_body["messages"] = retry_messages
            if _is_official_deepseek(active):
                retry_body = _deepseek_fast_mode(retry_body, max_tokens=1200)
            retry_payload = _post_json(
                client,
                endpoint=endpoint,
                headers=_headers(active),
                body=retry_body,
            )
            text = _response_text(retry_payload).strip()
    latency_ms = int((time.monotonic() - started) * 1000)
    if not text:
        raise ValueError("模型接口已响应，但预测正文为空；系统已关闭思考模式并自动重试，仍未获得结果")
    result = _extract_json(text)
    position = int(result.get("position", 0)) - 1
    if position not in range(10):
        raise ValueError("AI 返回的名次无效")
    raw_scores = result.get("scores")
    if not isinstance(raw_scores, list) or len(raw_scores) != 10:
        raise ValueError("AI 必须返回号码1至10的10项评分")
    scores = [float(value) for value in raw_scores]
    probabilities = _normalize(scores)
    ranked = sorted(range(10), key=lambda index: probabilities[index], reverse=True)
    analysis_text = _chinese_text(
        result.get("analysis"),
        "模型已完成独立统计比较；原始说明不是中文，已改用中文兜底说明。",
        240,
    )
    risk_text = _chinese_text(
        result.get("risk_note"),
        "样本量和随机性都可能造成偏差，不能保证未来结果，仅用于前向验证。",
        200,
    )
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
