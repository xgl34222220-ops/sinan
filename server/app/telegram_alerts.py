from __future__ import annotations

import hashlib
import html
import re
from typing import Any

import requests

from .config import settings


_TELEGRAM_API = "https://api.telegram.org"
_SPLIT_CHAT_IDS = re.compile(r"[\s,;]+")
_NATIVE_SOURCE = "native"
_NATIVE_SOURCE_FRAGMENT = "<b>来源：</b>天机云端本地"
_NATIVE_SUPPRESSED_MESSAGE = "Telegram 已忽略天机云端本地来源"


def parse_chat_ids(raw: str) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for item in _SPLIT_CHAT_IDS.split(raw.strip()):
        chat_id = item.strip()
        if not chat_id or chat_id in seen:
            continue
        seen.add(chat_id)
        values.append(chat_id)
    return tuple(values)


def delivery_key(chat_id: str) -> str:
    digest = hashlib.sha256(chat_id.encode("utf-8")).hexdigest()[:24]
    return f"telegram:{digest}"


def _is_native_alert(alert: Any) -> bool:
    try:
        return str(alert["source"]).strip().lower() == _NATIVE_SOURCE
    except (KeyError, TypeError, IndexError):
        return False


def _is_native_message(text: str) -> bool:
    return _NATIVE_SOURCE_FRAGMENT in str(text)


def _event_visual(streak: int, threshold: int) -> tuple[str, str]:
    if streak <= 2:
        return (
            "⚠️ <b>连续两期不中 · 提前预警</b>",
            "已连续两期 Top 6 未中，请留意下一期；每期云端 AI 预测仍会正常推送。",
        )
    if streak == threshold:
        return (
            "🚨🚨 <b>连续三期不中 · 加强提醒</b>",
            "已达到加强提醒条件，请重点关注下一期预测；后续每期预测仍会正常推送。",
        )
    return (
        f"🔴🔴 <b>连续 {streak} 期不中 · 升级提醒</b>",
        "连续未中仍在扩大，当前处于升级提醒状态；后续每期预测仍会正常推送。",
    )


def format_alert_message(alert: Any) -> str:
    lottery_name = html.escape(str(alert["lottery_name"]))
    source_name = html.escape(str(alert["source_name"]))
    model = html.escape(str(alert["model"]))
    streak = int(alert["streak"])
    threshold = int(alert["threshold"])
    latest_period = html.escape(str(alert["latest_target_period"]))

    try:
        recent_periods = [
            html.escape(str(value))
            for value in __import__("json").loads(str(alert["recent_periods_json"]))
            if str(value).strip()
        ]
    except (TypeError, ValueError):
        recent_periods = []

    heading, notice = _event_visual(streak, threshold)
    lines = [
        heading,
        "",
        f"🎯 <b>{lottery_name}</b> · {source_name}",
        f"🤖 <code>{model}</code>",
        f"📌 目标期：<code>{latest_period}</code>",
        f"📉 <b>连续未中：</b><b>{streak} 期</b>（Top 6）",
    ]
    if recent_periods:
        lines.append(f"🕘 最近期号：{'、'.join(recent_periods)}")
    lines.extend(["", notice])
    return "\n".join(lines)


def _base_url() -> str:
    base = settings.public_base_url.strip().rstrip("/")
    return base if base.startswith("https://") else ""


def prediction_reply_markup() -> dict[str, Any] | None:
    base = _base_url()
    if not base:
        return None
    return {
        "inline_keyboard": [
            [
                {"text": "🔮 查看预测", "url": base},
                {"text": "⚙️ 管理面板", "url": f"{base}/admin"},
            ]
        ]
    }


def alert_reply_markup() -> dict[str, Any] | None:
    base = _base_url()
    if not base:
        return None
    return {
        "inline_keyboard": [
            [
                {"text": "🚨 查看预警", "url": base},
                {"text": "⚙️ 管理面板", "url": f"{base}/admin"},
            ]
        ]
    }


# Backward-compatible helper kept for existing tests and older integrations.
def _reply_markup() -> dict[str, Any] | None:
    return alert_reply_markup()


def recovery_reply_markup() -> dict[str, Any] | None:
    base = _base_url()
    if not base:
        return None
    return {
        "inline_keyboard": [
            [
                {"text": "✅ 查看最新预测", "url": base},
                {"text": "📚 打开档案", "url": f"{base}/admin"},
            ]
        ]
    }


def _first_line(lines: list[str], prefix: str) -> str:
    return next((line for line in lines if line.startswith(prefix)), "")


def _compact_event_message(text: str) -> str:
    """Keep audit-rich event text in storage while rendering a cleaner Telegram card."""
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    if not lines:
        return str(text)

    if "新一期云端 AI 预测" in lines[0]:
        lottery = _first_line(lines, "<b>彩种：</b>")
        target = _first_line(lines, "<b>目标期：</b>")
        model = _first_line(lines, "<b>模型：</b>")
        position = _first_line(lines, "<b>预测名次：</b>")
        top6 = _first_line(lines, "<b>Top 6：</b>")
        status = next(
            (
                line
                for line in lines
                if line.startswith("<b>当前状态：</b>")
                or line.startswith("<b>🚨 加强关注：</b>")
            ),
            "",
        )
        result = ["🔮 <b>天机 AI · 新一期预测</b>", ""]
        result.extend(line for line in (lottery, target, position) if line)
        if top6:
            result.extend(["", top6])
        result.extend(line for line in (model, status) if line)
        return "\n".join(result)

    if "连续不中后恢复命中" in lines[0]:
        keep_prefixes = (
            "<b>彩种：</b>",
            "<b>开奖期号：</b>",
            "<b>模型：</b>",
            "<b>预测名次：</b>",
            "<b>预测 Top 6：</b>",
            "<b>实际号码：</b>",
            "<b>命中顺位：</b>",
        )
        result = ["✅ <b>天机 AI · 恢复命中</b>", ""]
        result.extend(line for line in lines if line.startswith(keep_prefixes))
        return "\n".join(result)

    return str(text)


def send_html_message(
    *,
    bot_token: str,
    chat_id: str,
    text: str,
    timeout_seconds: int = 6,
    disable_notification: bool = False,
    reply_markup: dict[str, Any] | None = None,
) -> tuple[bool, int | None, str]:
    token = bot_token.strip()
    target = chat_id.strip()
    if not token or not target:
        return False, None, "Telegram 配置不完整"
    if _is_native_message(text):
        return True, 204, _NATIVE_SUPPRESSED_MESSAGE

    is_prediction = "新一期云端 AI 预测" in text
    is_recovery = "连续不中后恢复命中" in text
    if reply_markup is None:
        if is_prediction:
            reply_markup = prediction_reply_markup()
        elif is_recovery:
            reply_markup = recovery_reply_markup()

    url = f"{_TELEGRAM_API}/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": target,
        "text": _compact_event_message(text),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        # Every-period prediction is intentionally quiet. Recovery/risk keeps attention.
        "disable_notification": bool(disable_notification or is_prediction),
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(url, json=payload, timeout=timeout_seconds)
        message = response.text[:800]
        return response.ok, int(response.status_code), message
    except requests.RequestException as exc:
        return False, None, str(exc)[:800]


def send_alert(
    *,
    bot_token: str,
    chat_id: str,
    alert: Any,
    timeout_seconds: int = 6,
) -> tuple[bool, int | None, str]:
    token = bot_token.strip()
    target = chat_id.strip()
    if not token or not target:
        return False, None, "Telegram 配置不完整"
    if _is_native_alert(alert):
        return True, 204, _NATIVE_SUPPRESSED_MESSAGE

    url = f"{_TELEGRAM_API}/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": target,
        "text": format_alert_message(alert),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "disable_notification": False,
    }
    markup = alert_reply_markup()
    if markup is not None:
        payload["reply_markup"] = markup
    try:
        response = requests.post(url, json=payload, timeout=timeout_seconds)
        text = response.text[:800]
        if response.ok:
            return True, int(response.status_code), text
        return False, int(response.status_code), text
    except requests.RequestException as exc:
        return False, None, str(exc)[:800]