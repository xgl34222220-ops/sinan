from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import json
import re
import time
from typing import Any

import requests

from .config import settings
from .db import database


_INSTALLED = False
_PROTOCOL_VERSION = 2
_DELIVERY_WINDOW_MS = 72 * 60 * 60 * 1000
_PREDICTION_EXPIRY_MS = 6 * 60 * 60 * 1000
_ALERT_EXPIRY_MS = 72 * 60 * 60 * 1000


def _now_ms() -> int:
    return int(time.time() * 1000)


def _table_exists(name: str) -> bool:
    with database.connection() as db:
        return db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone() is not None


def _plain_text(message_html: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", message_html, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return " · ".join(lines[:5])[:500]


def _event_metadata(row: Any) -> dict[str, Any]:
    try:
        data = json.loads(str(row["data_json"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        data = {}
    event_type = str(row["event_type"] or data.get("event_type") or "miss_alert")
    severity = str(row["severity"] or data.get("severity") or "warning")
    created_at = int(row["created_at"])
    expires_at = row["expires_at"]
    if expires_at is None:
        expires_at = created_at + (
            _PREDICTION_EXPIRY_MS if event_type == "prediction_ready" else _ALERT_EXPIRY_MS
        )
    collapse_key = str(
        row["collapse_key"]
        or data.get("collapse_key")
        or f"{row['lottery']}:{row['source']}:{row['model']}"
    )[:160]
    deep_link = str(
        row["deep_link"]
        or data.get("deep_link")
        or f"tianji://alerts/{int(row['id'])}"
    )[:500]
    return {
        "data": data,
        "event_type": event_type,
        "severity": severity,
        "expires_at": int(expires_at),
        "collapse_key": collapse_key,
        "deep_link": deep_link,
    }


def _alert_row_v2(row: Any) -> dict[str, Any]:
    from . import push_alerts

    value = push_alerts._ORIGINAL_ALERT_ROW_V2(row)
    metadata = _event_metadata(row)
    value.update(
        {
            "schema_version": int(row["schema_version"] or _PROTOCOL_VERSION),
            "event_type": metadata["event_type"],
            "severity": metadata["severity"],
            "deep_link": metadata["deep_link"],
            "collapse_key": metadata["collapse_key"],
            "expires_at_epoch_ms": metadata["expires_at"],
        }
    )
    return value


def _normalize_warning_rows(alert_ids: list[int]) -> None:
    if not alert_ids:
        return
    placeholders = ",".join("?" for _ in alert_ids)
    with database.connection() as db:
        db.execute(
            f"""
            UPDATE push_alerts SET
                schema_version=2,
                event_type=CASE
                    WHEN streak<=2 THEN 'miss_prealert'
                    WHEN streak=threshold THEN 'miss_alert'
                    ELSE 'miss_escalation'
                END,
                severity=CASE
                    WHEN streak<=2 THEN 'info'
                    WHEN streak=threshold THEN 'warning'
                    ELSE 'critical'
                END,
                deep_link='tianji://alerts/' || id,
                collapse_key=lottery || ':' || source || ':' || model,
                expires_at=created_at + ?
            WHERE id IN ({placeholders})
            """,
            (_ALERT_EXPIRY_MS, *alert_ids),
        )


def _mirror_telegram_events(lottery_filter: str | None = None) -> list[int]:
    if not _table_exists("telegram_events"):
        return []
    params: list[Any] = [_now_ms() - 7 * 86_400_000]
    lottery_sql = ""
    if lottery_filter:
        lottery_sql = " AND lottery=?"
        params.append(lottery_filter)
    with database.connection() as db:
        rows = db.execute(
            f"""
            SELECT event_key,event_type,lottery,source,model,target_period,
                   message_html,created_at
            FROM telegram_events
            WHERE created_at>=?{lottery_sql}
            ORDER BY created_at DESC
            LIMIT 1000
            """,
            tuple(params),
        ).fetchall()

        inserted: list[int] = []
        for row in rows:
            source_event = str(row["event_type"])
            if source_event == "prediction":
                event_type = "prediction_ready"
                severity = "info"
                title = "新一期云端 AI 预测"
                expiry = int(row["created_at"]) + _PREDICTION_EXPIRY_MS
            elif source_event == "win":
                event_type = "hit_recovery"
                severity = "success"
                title = "连续不中后恢复命中"
                expiry = int(row["created_at"]) + _ALERT_EXPIRY_MS
            else:
                continue
            body = _plain_text(str(row["message_html"]))
            event_key = f"unified:{row['event_key']}"
            lottery = str(row["lottery"])
            source = str(row["source"])
            model = str(row["model"])
            target_period = str(row["target_period"])
            data = {
                "schema_version": "2",
                "event_type": event_type,
                "severity": severity,
                "lottery": lottery,
                "lottery_name": lottery,
                "source": source,
                "source_name": "天机云端 AI" if source == "ai" else source,
                "model": model,
                "latest_target_period": target_period,
                "title": title,
                "body": body,
                "deep_link": "tianji://alerts",
                "collapse_key": f"{lottery}:{source}:{model}",
                "expires_at_epoch_ms": str(expiry),
            }
            cursor = db.execute(
                """
                INSERT OR IGNORE INTO push_alerts(
                    event_key,lottery,lottery_name,source,source_name,model,
                    streak,threshold,latest_target_period,recent_periods_json,
                    title,body,data_json,created_at,schema_version,event_type,
                    severity,deep_link,collapse_key,expires_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    event_key,
                    lottery,
                    lottery,
                    source,
                    "天机云端 AI" if source == "ai" else source,
                    model,
                    0,
                    max(3, int(settings.push_threshold)),
                    target_period,
                    json.dumps([target_period], ensure_ascii=False),
                    title,
                    body,
                    json.dumps(data, ensure_ascii=False),
                    int(row["created_at"]),
                    2,
                    event_type,
                    severity,
                    "tianji://alerts",
                    f"{lottery}:{source}:{model}",
                    expiry,
                ),
            )
            if cursor.rowcount:
                inserted.append(int(cursor.lastrowid))
        return inserted


def _send_fcm_v2(token: str, alert: Any) -> tuple[bool, int | None, str]:
    from . import push_alerts

    credentials = push_alerts._credentials()
    if credentials is None or not credentials.token:
        return False, None, "FCM 尚未配置"

    metadata = _event_metadata(alert)
    try:
        raw_data = json.loads(str(alert["data_json"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        raw_data = {}
    data = {
        **{str(key): str(value) for key, value in raw_data.items()},
        "schema_version": str(int(alert["schema_version"] or _PROTOCOL_VERSION)),
        "event_type": metadata["event_type"],
        "severity": metadata["severity"],
        "alert_id": str(int(alert["id"])),
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
        "recent_periods": ",".join(str(value) for value in json.loads(str(alert["recent_periods_json"]))),
        "deep_link": metadata["deep_link"],
        "collapse_key": metadata["collapse_key"],
        "expires_at_epoch_ms": str(metadata["expires_at"]),
    }
    ttl_seconds = max(60, min(259_200, (metadata["expires_at"] - _now_ms()) // 1000))
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
                "priority": "HIGH" if metadata["severity"] in {"warning", "critical"} else "NORMAL",
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
        return response.ok, int(response.status_code), response.text[:800]
    except requests.RequestException as exc:
        return False, None, str(exc)[:800]


def _delivery_candidates() -> tuple[list[Any], list[Any]]:
    now = _now_ms()
    retry_before = now - max(60, settings.push_retry_seconds) * 1000
    lower_bound = now - _DELIVERY_WINDOW_MS
    with database.connection() as db:
        fcm_rows = db.execute(
            """
            SELECT
                a.*,
                d.installation_id AS target_installation_id,
                d.fcm_token AS target_fcm_token,
                d.enabled AS device_enabled,
                d.xyft_enabled AS device_xyft_enabled,
                d.azxy10_enabled AS device_azxy10_enabled,
                d.ai_enabled AS device_ai_enabled,
                d.native_enabled AS device_native_enabled,
                d.escalation_enabled AS device_escalation_enabled,
                d.updated_at AS device_updated_at
            FROM push_alerts AS a
            CROSS JOIN push_devices AS d
            LEFT JOIN push_deliveries AS delivery
              ON delivery.alert_id=a.id
             AND delivery.installation_id=d.installation_id
            WHERE d.enabled=1
              AND d.fcm_token<>''
              AND a.created_at>=?
              AND (a.expires_at IS NULL OR a.expires_at>?)
              AND (
                    delivery.alert_id IS NULL
                    OR (
                        delivery.status<>'sent'
                        AND delivery.attempted_at<=?
                    )
                  )
            ORDER BY a.id DESC, d.updated_at DESC
            LIMIT 2000
            """,
            (lower_bound, now, retry_before),
        ).fetchall()
        alerts = db.execute(
            """
            SELECT * FROM push_alerts
            WHERE created_at>=?
              AND (expires_at IS NULL OR expires_at>?)
            ORDER BY id DESC
            LIMIT 200
            """,
            (lower_bound, now),
        ).fetchall()
    return fcm_rows, alerts


def _device_accepts_candidate(row: Any) -> bool:
    if not bool(row["device_enabled"]):
        return False
    lottery = str(row["lottery"])
    source = str(row["source"])
    event_type = str(row["event_type"])
    if lottery == "xyft" and not bool(row["device_xyft_enabled"]):
        return False
    if lottery == "azxy10" and not bool(row["device_azxy10_enabled"]):
        return False
    if source == "ai" and not bool(row["device_ai_enabled"]):
        return False
    if source == "native" and not bool(row["device_native_enabled"]):
        return False
    if event_type == "miss_escalation" and not bool(row["device_escalation_enabled"]):
        return False
    return True


def _store_result(
    row: Any,
    *,
    target_key: str,
    ok: bool,
    code: int | None,
    message: str,
) -> None:
    from . import push_alerts

    push_alerts._store_delivery(
        alert_id=int(row["id"]),
        target_key=target_key,
        ok=ok,
        code=code,
        message=message,
        attempted_at=_now_ms(),
    )
    if not ok and code in {400, 404} and (
        "UNREGISTERED" in message or "registration-token-not-registered" in message
    ):
        with database.connection() as db:
            db.execute(
                "UPDATE push_devices SET fcm_token='',updated_at=? WHERE installation_id=?",
                (_now_ms(), target_key),
            )


def _deliver_fcm(row: Any) -> tuple[bool, str]:
    target_key = str(row["target_installation_id"])
    ok, code, message = _send_fcm_v2(str(row["target_fcm_token"]), row)
    _store_result(row, target_key=target_key, ok=ok, code=code, message=message)
    return ok, target_key


def _deliver_pending_alerts_v2() -> dict[str, int]:
    from . import push_alerts, telegram_alerts

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

    fcm_rows, alerts = _delivery_candidates()
    accepted = [row for row in fcm_rows if _device_accepts_candidate(row)]
    skipped = len(fcm_rows) - len(accepted)
    fcm_sent = fcm_failed = 0

    if settings.fcm_enabled and accepted:
        with ThreadPoolExecutor(
            max_workers=max(1, settings.push_delivery_workers),
            thread_name_prefix="tianji-fcm",
        ) as pool:
            futures = [pool.submit(_deliver_fcm, row) for row in accepted]
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
    retry_before = _now_ms() - max(60, settings.push_retry_seconds) * 1000
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
                (_now_ms() - _DELIVERY_WINDOW_MS,),
            ).fetchall()
        deliveries = {
            (int(row["alert_id"]), str(row["installation_id"])): dict(row)
            for row in delivery_rows
        }
        for alert in alerts:
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
                    attempted_at=_now_ms(),
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


def _process_prediction_alerts_v2(lottery_key: str | None = None) -> dict[str, Any]:
    from . import push_alerts

    watch = push_alerts.prediction_miss_watch(threshold=push_alerts.PREALERT_THRESHOLD)
    warning_ids = push_alerts.materialize_warning_alerts(
        watch,
        lottery_filter=lottery_key,
    )
    _normalize_warning_rows(warning_ids)
    mirrored_ids = _mirror_telegram_events(lottery_key)
    delivery = _deliver_pending_alerts_v2()
    return {
        "created_alert_ids": warning_ids + mirrored_ids,
        "delivery": delivery,
        "protocol_version": _PROTOCOL_VERSION,
        "push_configured": settings.fcm_enabled or settings.telegram_enabled,
        "channels": {
            "fcm": settings.fcm_enabled,
            "telegram": settings.telegram_enabled,
        },
    }


def _verify_device_row(installation_id: str, secret: str) -> dict[str, Any]:
    from . import push_alerts

    return push_alerts._verify_device(installation_id, secret)


def _device_status_v2(installation_id: str, secret: str) -> dict[str, Any]:
    from . import push_alerts

    row = _verify_device_row(installation_id, secret)
    prefs = push_alerts._row_preferences(row)
    cursor = int(row.get("read_through_alert_id") or 0)
    with database.connection() as db:
        unread = int(
            db.execute(
                """
                SELECT COUNT(*) FROM push_alerts AS a
                LEFT JOIN push_alert_reads AS r
                  ON r.alert_id=a.id AND r.installation_id=?
                WHERE a.id>?
                  AND r.alert_id IS NULL
                """,
                (installation_id, cursor),
            ).fetchone()[0]
        )
    return {
        "installation_id": installation_id,
        "registered": True,
        "protocol_version": _PROTOCOL_VERSION,
        "fcm_token_present": bool(row.get("fcm_token")),
        "push_configured": settings.fcm_enabled,
        "fallback_poll_minutes": 15,
        "unread_count": unread,
        "read_through_alert_id": cursor,
        "preferences": prefs.as_dict(),
        "updated_at_epoch_ms": int(row["updated_at"]),
    }


def _list_alerts_v2(
    installation_id: str,
    secret: str,
    *,
    limit: int = 100,
    after_id: int = 0,
) -> dict[str, Any]:
    row = _verify_device_row(installation_id, secret)
    cursor = int(row.get("read_through_alert_id") or 0)
    safe_limit = max(1, min(200, int(limit)))
    safe_after = max(0, int(after_id))
    with database.connection() as db:
        rows = db.execute(
            """
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
            ORDER BY a.id DESC
            LIMIT ?
            """,
            (cursor, installation_id, safe_after, safe_limit),
        ).fetchall()
        db.execute(
            """
            UPDATE push_devices
            SET last_seen_at=?,protocol_version=2
            WHERE installation_id=?
            """,
            (_now_ms(), installation_id),
        )
    return {
        "items": [_alert_row_v2(value) for value in rows],
        "protocol_version": _PROTOCOL_VERSION,
        "push_configured": settings.fcm_enabled,
        "generated_at_epoch_ms": _now_ms(),
    }


def _mark_all_read_v2(installation_id: str, secret: str) -> dict[str, Any]:
    _verify_device_row(installation_id, secret)
    now = _now_ms()
    with database.connection() as db:
        latest = int(db.execute("SELECT COALESCE(MAX(id),0) FROM push_alerts").fetchone()[0])
        db.execute(
            """
            UPDATE push_devices
            SET read_through_alert_id=MAX(read_through_alert_id,?),
                updated_at=?,last_seen_at=?
            WHERE installation_id=?
            """,
            (latest, now, now, installation_id),
        )
        db.execute(
            "DELETE FROM push_alert_reads WHERE installation_id=? AND alert_id<=?",
            (installation_id, latest),
        )
    return {
        "ok": True,
        "read_at_epoch_ms": now,
        "read_through_alert_id": latest,
    }


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from . import push_alerts

    push_alerts._ORIGINAL_ALERT_ROW_V2 = push_alerts._alert_row
    push_alerts._alert_row = _alert_row_v2
    push_alerts._send_fcm = _send_fcm_v2
    push_alerts.deliver_pending_alerts = _deliver_pending_alerts_v2
    push_alerts.process_prediction_alerts = _process_prediction_alerts_v2
    push_alerts.device_status = _device_status_v2
    push_alerts.list_alerts = _list_alerts_v2
    push_alerts.mark_all_read = _mark_all_read_v2
    _INSTALLED = True
