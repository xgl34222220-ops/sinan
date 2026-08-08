from __future__ import annotations

from contextlib import contextmanager
import threading
import time
from typing import Any

import httpx

from . import ai_ensemble, service
from .models import compact_json


# Five-minute lotteries must leave enough time for the prediction to reach the user
# before the draw/close window. A result that finishes inside this guard is discarded.
AI_PUBLISH_GUARD_MS = 90_000
# Three position reviewers + two number reviewers now run in parallel per phase.
# 225 seconds leaves ~135 seconds of AI work before the 90-second publish guard.
AI_MIN_START_LEAD_MS = 225_000
AI_FIRST_ATTEMPT_TIMEOUT_SECONDS = 45
AI_RETRY_TIMEOUT_SECONDS = 20
AI_MAX_FAST_TOKENS = 900

_INSTALLED = False
_CONTEXT = threading.local()
_ORIGINAL_RUN_PREFIX_CACHED = ai_ensemble._run_prefix_cached
_ORIGINAL_AI_ANALYZE = service.ai.analyze
_ORIGINAL_CALL_JSON = ai_ensemble._call_json


def _fast_context_enabled() -> bool:
    return bool(getattr(_CONTEXT, "deadline_fast", False))


@contextmanager
def _deadline_fast_context() -> Any:
    previous = _fast_context_enabled()
    _CONTEXT.deadline_fast = True
    try:
        yield
    finally:
        _CONTEXT.deadline_fast = previous


def _run_prefix_cached_deadline_aware(count: int, task: Any) -> list[Any]:
    """Keep the cache helper for tests/tools, but use true parallel reviews live.

    The old live path warmed reviewer 0 and only then started the remaining reviewers.
    That doubled wall-clock latency for every mandatory phase. Reviewer prompts still use
    the same neutral shared prefix, so providers may cache independently without making
    live prediction wait for an artificial warm-up request.
    """
    if _fast_context_enabled():
        return ai_ensemble._run_parallel(count, task)
    return _ORIGINAL_RUN_PREFIX_CACHED(count, task)


def _ai_analyze_deadline_fast(*args: Any, **kwargs: Any) -> Any:
    """Enable the fast review context without replacing the v2 continual engine itself."""
    with _deadline_fast_context():
        return _ORIGINAL_AI_ANALYZE(*args, **kwargs)


def _is_deepseek_like(config: Any) -> bool:
    return "deepseek" in str(getattr(config, "model", "")).lower()


def _fast_call_json(
    config: Any,
    *,
    system_prompt: str,
    user_payload: dict[str, Any] | None = None,
    shared_payload: dict[str, Any] | None = None,
    reviewer_payload: dict[str, Any] | None = None,
    max_tokens: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Deadline-oriented JSON call for server realtime prediction.

    DeepSeek reasoning is disabled on the first request instead of only after a failure.
    Unknown OpenAI-compatible gateways that reject `thinking` or `response_format` are
    retried immediately without those optional fields. Output is intentionally capped:
    reviewers are required to return compact JSON, not long prose.
    """
    if not _fast_context_enabled():
        return _ORIGINAL_CALL_JSON(
            config,
            system_prompt=system_prompt,
            user_payload=user_payload,
            shared_payload=shared_payload,
            reviewer_payload=reviewer_payload,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )

    endpoint = str(config.endpoint).rstrip("/")
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

    token_cap = min(max(256, int(max_tokens)), AI_MAX_FAST_TOKENS)
    if is_responses:
        body: dict[str, Any] = {
            "model": config.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_output_tokens": token_cap,
        }
    else:
        body = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "stream": False,
            "response_format": {"type": "json_object"},
            "max_tokens": token_cap,
        }
        if _is_deepseek_like(config):
            body["thinking"] = {"type": "disabled"}

    last_error: Exception | None = None
    for attempt in range(ai_ensemble._MAX_ATTEMPTS_PER_REVIEWER):
        request_body = dict(body)
        if attempt > 0 and not is_responses:
            request_body.pop("response_format", None)
            request_body["max_tokens"] = min(AI_MAX_FAST_TOKENS + 200, max_tokens + 200)
        try:
            configured = max(5, min(int(timeout_seconds), int(config.timeout_seconds)))
            attempt_timeout = min(
                configured,
                AI_FIRST_ATTEMPT_TIMEOUT_SECONDS if attempt == 0 else AI_RETRY_TIMEOUT_SECONDS,
            )
            with httpx.Client(
                timeout=httpx.Timeout(attempt_timeout, connect=min(10.0, attempt_timeout)),
                follow_redirects=True,
            ) as client:
                response = client.post(
                    endpoint,
                    headers=ai_ensemble._headers(config),
                    json=request_body,
                )
                if response.status_code >= 400 and not is_responses:
                    compatibility_body = dict(request_body)
                    compatibility_body.pop("thinking", None)
                    compatibility_body.pop("response_format", None)
                    if compatibility_body != request_body:
                        response = client.post(
                            endpoint,
                            headers=ai_ensemble._headers(config),
                            json=compatibility_body,
                        )
                response.raise_for_status()
                payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("AI 接口返回格式异常")
            response_text = ai_ensemble._response_text(payload).strip()
            if not response_text:
                raise ValueError("AI 最终正文为空")
            parsed = ai_ensemble._extract_json(response_text)
            parsed["_tianji_usage"] = ai_ensemble._usage_from_response(payload)
            return parsed
        except Exception as exc:  # noqa: BLE001 - provider failures get one bounded retry
            last_error = exc
    raise RuntimeError(f"AI 独立评审失败：{str(last_error)[:240]}")


def _minimum_ai_lead_ms(_ai_config: Any) -> int:
    # Do not start a fresh AI job unless the mandatory two-phase parallel review has
    # enough budget to finish before the publish guard.
    return AI_MIN_START_LEAD_MS


def _target_is_open_with_publish_guard(
    spec: Any,
    trained_through_period: str,
    target_period: str,
) -> bool:
    latest, current_next_period, _, next_draw_at = service.lottery_client.fetch_latest(spec)
    if latest.period != trained_through_period or current_next_period != target_period:
        return False
    if next_draw_at is not None:
        now = int(time.time() * 1000)
        if now >= int(next_draw_at) - AI_PUBLISH_GUARD_MS:
            return False
    return service.database.get_draw(spec.key, target_period) is None


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ai_ensemble._run_prefix_cached = _run_prefix_cached_deadline_aware
    ai_ensemble._call_json = _fast_call_json
    service.ai.analyze = _ai_analyze_deadline_fast
    service._minimum_ai_lead_ms = _minimum_ai_lead_ms
    service._target_is_open = _target_is_open_with_publish_guard
    _INSTALLED = True
