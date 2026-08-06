from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from typing import Any

import requests

from . import push_alerts, push_runtime_bridge, push_runtime_v2, telegram_alerts
from .db import database


_INSTALLED = False


def _safe_strings(raw: Any) -> list[str]:
    try:
        value = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _send_fcm_fixed(token: str, alert: Any) -> tuple[bool, int | None, str]:
    credentials = push_alerts._credentials()
    if credentials is None or not credentials.token:
        return False, None, "FCM 尚未配置"

    metadata = push_runtime_v2._event_metadata(alert)
    try:
        raw_data = json.loads(str(alert["data_json"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        raw_data = {}
    data = {
        **{str(key): str(value) for key, value in raw_data.items()},
        "schema_version": str(
            int(alert["schema_version"] or push_runtime_v2._PROTOCOL_VERSION)
        ),
        "event_type": metadata["event_type"],
        "severity": metadata["severity"],
        "alert_id": str(int(alert["id"])),
        "open_alert_center": "true",
        "title": str(alert["title"]),
        "body": str(alert["body"]),
        "lottery": str(alert["lottery"]),
        "lottery_name": str(alert["lottery_name"]),
        "source": str(alert["source"]),
        "source_name": str(alert["source_name"]),
        "model": str(alert["model"]),
        "streak": str(int(alert["streak"])),
        "threshold": str(int(alert["threshold"])),
        "latest_target_period": str(alert["latest_target_period"]),
        "recent_periods": ",".join(_safe_strings(alert["recent_periods_json"])),
        "deep_link": metadata["deep_link"],
        "collapse_key": metadata["collapse_key"],
        "expires_at_epoch_ms": str(metadata["expires_at"]),
    }
    ttl_seconds = max(
        60,
        min(259_200, (metadata["expires_at"] - push_runtime_v2._now_ms()) // 1000),
    )
    channel_id = (
        "tianji_prediction_updates"
        if metadata["event_type"] in {"prediction_ready", "hit_recovery"}
        else push_alerts.CHANNEL_ID
    )
    payload = {
        "message": {
            "token": token,
            "notification": {
                "title": str(alert["title"]),
                "body": str(alert["body"]),
            },
            "data": data,
            "android": {
                "priority": (
                    "HIGH"
                    if metadata["severity"] in {"warning", "critical"}
                    else "NORMAL"
                ),
                "collapse_key": metadata["collapse_key"],
                "ttl": f"{ttl_seconds}s",
                "notification": {
                    "channel_id": channel_id,
                    "default_sound": metadata["severity"] in {"warning", "critical"},
                    "tag": metadata["collapse_key"],
                },
            },
        }
    }
    url = (
        "https://fcm.googleapis.com/v1/projects/"
        f"{push_runtime_v2.settings.fcm_project_id}/messages:send"
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
        return response.ok, int(response.status_code), response.text[:800]
    except requests.RequestException as exc:
        return False, None, str(exc)[:800]


def _deliver_pending_fixed() -> dict[str, int]:
    settings = push_runtime_v2.settings
    if not settings.fcm_enabled and not settings.telegram_enabled:
        return {
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "fcm_sent": 0,
            "fcm_failed": 0,
            "telegram_sent": 0,
            "telegram_failed": 0,
        }

    fcm_rows, alerts = push_runtime_v2._delivery_candidates()
    accepted = [
        row for row in fcm_rows if push_runtime_v2._device_accepts_candidate(row)
    ]
    skipped = len(fcm_rows) - len(accepted)
    fcm_sent = fcm_failed = 0

    if settings.fcm_enabled and accepted:
        with ThreadPoolExecutor(
            max_workers=max(1, settings.push_delivery_workers),
            thread_name_prefix="tianji-fcm",
        ) as pool:
            futures = [pool.submit(push_runtime_v2._deliver_fcm, row) for row in accepted]
            for future in as_completed(futures):
                try:
                    ok, _ = future.result()
                except Exception:
                    ok = False
                if ok:
                    fcm_sent += 1
                else:
                    fcm_failed += 1

    telegram_sent = telegram_failed = 0
    retry_before = (
        push_runtime_v2._now_ms() - max(60, settings.push_retry_seconds) * 1000
    )
    if settings.telegram_enabled:
        with database.connection() as db:
            delivery_rows = db.execute(
                """
                SELECT alert_id,installation_id,status,attempted_at
                FROM push_deliveries
                WHERE alert_id IN (
                    SELECT id FROM push_alerts
                    WHERE created_at>=?
                    ORDER BY id DESC LIMIT 200
                )
                """,
                (push_runtime_v2._now_ms() - push_runtime_v2._DELIVERY_WINDOW_MS,),
            ).fetchall()
        deliveries = {
            (int(row["alert_id"]), str(row["installation_id"])): dict(row)
            for row in delivery_rows
        }
        for alert in alerts:
            # prediction_ready / hit_recovery originated in telegram_events and were
            # mirrored only for App/FCM history. Sending them here would duplicate Telegram.
            if str(alert["event_type"]) in {"prediction_ready", "hit_recovery"}:
                continue
            for chat_id in settings.telegram_chat_ids:
                target_key = telegram_alerts.delivery_key(chat_id)
                if not push_alerts._delivery_allowed(
                    deliveries,
                    alert_id=int(alert["id"]),
                    target_key=target_key,
                    retry_before=retry_before,
                ):
                    continue
                ok, code, message = telegram_alerts.send_alert(
                    bot_token=settings.telegram_bot_token,
                    chat_id=chat_id,
                    alert=alert,
                )
                push_alerts._store_delivery(
                    alert_id=int(alert["id"]),
                    target_key=target_key,
                    ok=ok,
                    code=code,
                    message=message,
                    attempted_at=push_runtime_v2._now_ms(),
                )
                if ok:
                    telegram_sent += 1
                else:
                    telegram_failed += 1

    return {
        "sent": fcm_sent + telegram_sent,
        "failed": fcm_failed + telegram_failed,
        "skipped": skipped,
        "fcm_sent": fcm_sent,
        "fcm_failed": fcm_failed,
        "telegram_sent": telegram_sent,
        "telegram_failed": telegram_failed,
    }


def _list_alerts_fixed(
    installation_id: str,
    secret: str,
    *,
    limit: int = 100,
    after_id: int = 0,
) -> dict[str, Any]:
    row = push_runtime_v2._verify_device_row(installation_id, secret)
    read_cursor = int(row.get("read_through_alert_id") or 0)
    safe_limit = max(1, min(200, int(limit)))
    safe_after = max(0, int(after_id))
    # Initial sync intentionally returns the latest history. Incremental sync must be
    # ascending so a batch limit cannot skip IDs between the old and newest cursor.
    order = "ASC" if safe_after > 0 else "DESC"
    with database.connection() as db:
        rows = db.execute(
            f"""
            SELECT
                a.*,
                CASE
                    WHEN a.id<=? THEN 1
                    WHEN r.alert_id IS NULL THEN 0
                    ELSE 1
                END AS is_read
            FROM push_alerts AS a
            LEFT JOIN push_alert_reads AS r
              ON r.alert_id=a.id AND r.installation_id=?
            WHERE a.id>?
            ORDER BY a.id {order}
            LIMIT ?
            """,
            (read_cursor, installation_id, safe_after, safe_limit),
        ).fetchall()
        db.execute(
            """
            UPDATE push_devices
            SET last_seen_at=?,protocol_version=2
            WHERE installation_id=?
            """,
            (push_runtime_v2._now_ms(), installation_id),
        )
    return {
        "items": [push_runtime_v2._alert_row_v2(value) for value in rows],
        "protocol_version": push_runtime_v2._PROTOCOL_VERSION,
        "push_configured": push_runtime_v2.settings.fcm_enabled,
        "generated_at_epoch_ms": push_runtime_v2._now_ms(),
    }


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    push_runtime_v2._send_fcm_v2 = _send_fcm_fixed
    push_runtime_v2._deliver_pending_alerts_v2 = _deliver_pending_fixed
    push_alerts._send_fcm = _send_fcm_fixed
    push_alerts.deliver_pending_alerts = push_runtime_bridge._dynamic_settings(
        _deliver_pending_fixed
    )
    push_alerts.list_alerts = _list_alerts_fixed
    _INSTALLED = True
