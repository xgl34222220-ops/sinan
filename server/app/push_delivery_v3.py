from __future__ import annotations

import json
from typing import Any

import requests

from .config import settings


SCHEMA_VERSION = 2


def _legacy_event_type(alert: Any, data: dict[str, Any]) -> str:
    explicit = str(data.get("event_type") or "").strip()
    if explicit:
        return explicit
    raw_type = str(data.get("type") or "").strip()
    if raw_type and raw_type != "prediction_miss_alert":
        return raw_type
    streak = int(alert["streak"] or 0)
    threshold = int(alert["threshold"] or 3)
    if streak <= 2:
        return "miss_prealert"
    if streak > threshold:
        return "miss_escalation"
    return "miss_alert"


def _severity(event_type: str) -> str:
    if event_type == "hit_recovery":
        return "success"
    if event_type == "miss_escalation":
        return "critical"
    if event_type in {"miss_prealert", "miss_alert", "service_warning"}:
        return "warning"
    return "info"


def message_data(alert: Any) -> dict[str, str]:
    try:
        data = json.loads(str(alert["data_json"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    event_type = _legacy_event_type(alert, data)
    collapse_key = str(data.get("collapse_key") or "").strip() or ":".join(
        [
            str(alert["lottery"] or "general"),
            str(alert["source"] or "general"),
            str(alert["model"] or "general"),
        ]
    )
    recent = json.loads(str(alert["recent_periods_json"] or "[]"))
    if not isinstance(recent, list):
        recent = []

    data.update(
        {
            "alert_id": str(alert["id"]),
            "event_key": str(alert["event_key"] or ""),
            "lottery": str(alert["lottery"] or ""),
            "lottery_name": str(alert["lottery_name"] or ""),
            "source": str(alert["source"] or ""),
            "source_name": str(alert["source_name"] or ""),
            "model": str(alert["model"] or ""),
            "streak": str(alert["streak"] or 0),
            "threshold": str(alert["threshold"] or 3),
            "latest_target_period": str(alert["latest_target_period"] or ""),
            "recent_periods": ",".join(str(item) for item in recent if str(item).strip()),
            "title": str(alert["title"] or ""),
            "body": str(alert["body"] or ""),
            "created_at_epoch_ms": str(alert["created_at"] or 0),
            "schema_version": str(SCHEMA_VERSION),
            "event_type": event_type,
            "severity": str(data.get("severity") or _severity(event_type)),
            "deep_link": str(data.get("deep_link") or "tianji://alerts"),
            "collapse_key": collapse_key,
        }
    )
    return {str(key): str(value) for key, value in data.items()}


def send_data_message(push_alerts_module: Any, token: str, alert: Any) -> tuple[bool, int | None, str]:
    credentials = push_alerts_module._credentials()  # noqa: SLF001 - compatibility patch
    if credentials is None or not credentials.token:
        return False, None, "FCM 尚未配置"

    data = message_data(alert)
    collapse_key = data.get("collapse_key", "tianji_general")[:64]
    payload = {
        "message": {
            "token": token,
            # Deliberately data-only. Android always passes this through
            # TianjiMessagingService, so the App selects the correct normal/risk
            # channel instead of Firebase rendering every event as a risk alert.
            "data": data,
            "android": {
                "priority": "HIGH",
                "ttl": "900s",
                "collapse_key": collapse_key,
                "direct_boot_ok": False,
            },
        }
    }
    url = (
        "https://fcm.googleapis.com/v1/projects/"
        f"{settings.fcm_project_id}/messages:send"
    )
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json=payload,
            timeout=12,
        )
        message = response.text[:800]
        return response.ok, int(response.status_code), message
    except requests.RequestException as exc:
        return False, None, str(exc)[:800]


def install(push_alerts_module: Any) -> None:
    if getattr(push_alerts_module, "_tianji_data_only_fcm", False):
        return

    def _send(token: str, alert: Any) -> tuple[bool, int | None, str]:
        return send_data_message(push_alerts_module, token, alert)

    push_alerts_module._send_fcm = _send  # noqa: SLF001 - intentional runtime compatibility
    push_alerts_module._tianji_data_only_fcm = True
