from __future__ import annotations

import hashlib
import html
import re
from typing import Any

import requests


_TELEGRAM_API = "https://api.telegram.org"
_SPLIT_CHAT_IDS = re.compile(r"[\s,;]+")


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


def format_alert_message(alert: Any) -> str:
    title = html.escape(str(alert["title"]))
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

    level = "🔴" if streak > threshold else "⚠️"
    lines = [
        f"{level} <b>{title}</b>",
        "",
        f"<b>彩种：</b>{lottery_name}",
        f"<b>来源：</b>{source_name}",
        f"<b>模型：</b><code>{model}</code>",
        f"<b>连续未中：</b>{streak} 期（Top 6）",
        f"<b>最新目标期：</b><code>{latest_period}</code>",
    ]
    if recent_periods:
        lines.append(f"<b>最近期号：</b>{'、'.join(recent_periods)}")
    lines.extend(
        [
            "",
            "同一预警只发送一次；命中后清零，重新连续三期不中才会再次提醒。",
        ]
    )
    return "\n".join(lines)


def send_html_message(
    *,
    bot_token: str,
    chat_id: str,
    text: str,
    timeout_seconds: int = 12,
    disable_notification: bool = False,
) -> tuple[bool, int | None, str]:
    token = bot_token.strip()
    target = chat_id.strip()
    if not token or not target:
        return False, None, "Telegram 配置不完整"

    url = f"{_TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": target,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "disable_notification": disable_notification,
    }
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
    timeout_seconds: int = 12,
) -> tuple[bool, int | None, str]:
    token = bot_token.strip()
    target = chat_id.strip()
    if not token or not target:
        return False, None, "Telegram 配置不完整"

    url = f"{_TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": target,
        "text": format_alert_message(alert),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "disable_notification": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=timeout_seconds)
        text = response.text[:800]
        if response.ok:
            return True, int(response.status_code), text
        return False, int(response.status_code), text
    except requests.RequestException as exc:
        return False, None, str(exc)[:800]
