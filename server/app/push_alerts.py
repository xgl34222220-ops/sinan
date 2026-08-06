from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass
from typing import Any

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from .admin_insights import prediction_miss_watch
from .config import settings
from .db import database
from .models import LOTTERIES
from . import telegram_alerts


CHANNEL_ID = "tianji_prediction_alerts"
PREALERT_THRESHOLD = 2
STRONG_ALERT_THRESHOLD = 3
_INIT_LOCK = threading.Lock()
_INITIALIZED = False
_CREDENTIAL_LOCK = threading.Lock()
_CREDENTIALS: service_account.Credentials | None = None


@dataclass(frozen=True)
class DevicePreferences:
    enabled: bool = True
    xyft_enabled: bool = True
    azxy10_enabled: bool = True
    ai_enabled: bool = True
    native_enabled: bool = True
    escalation_enabled: bool = True

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "DevicePreferences":
        raw = value or {}
        return cls(
            enabled=bool(raw.get("enabled", True)),
            xyft_enabled=bool(raw.get("xyft_enabled", True)),
            azxy10_enabled=bool(raw.get("azxy10_enabled", True)),
            ai_enabled=bool(raw.get("ai_enabled", True)),
            native_enabled=bool(raw.get("native_enabled", True)),
            escalation_enabled=bool(raw.get("escalation_enabled", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "enabled": self.enabled,
            "xyft_enabled": self.xyft_enabled,
            "azxy10_enabled": self.azxy10_enabled,
            "ai_enabled": self.ai_enabled,
            "native_enabled": self.native_enabled,
            "escalation_enabled": self.escalation_enabled,
        }


def _now_ms() -> int:
    return int(time.time() * 1000)


def _secret_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def initialize() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    with _INIT_LOCK:
        if _INITIALIZED:
            return
        with database.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS push_devices (
                    installation_id TEXT PRIMARY KEY,
                    secret_hash TEXT NOT NULL,
                    fcm_token TEXT NOT NULL DEFAULT '',
                    platform TEXT NOT NULL DEFAULT 'android',
                    app_version TEXT NOT NULL DEFAULT '',
                    device_name TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    xyft_enabled INTEGER NOT NULL DEFAULT 1,
                    azxy10_enabled INTEGER NOT NULL DEFAULT 1,
                    ai_enabled INTEGER NOT NULL DEFAULT 1,
                    native_enabled INTEGER NOT NULL DEFAULT 1,
                    escalation_enabled INTEGER NOT NULL DEFAULT 1,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    last_seen_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS push_devices_updated
                    ON push_devices(updated_at DESC);

                CREATE TABLE IF NOT EXISTS push_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_key TEXT NOT NULL UNIQUE,
                    lottery TEXT NOT NULL,
                    lottery_name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    model TEXT NOT NULL,
                    streak INTEGER NOT NULL,
                    threshold INTEGER NOT NULL,
                    latest_target_period TEXT NOT NULL,
                    recent_periods_json TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS push_alerts_created
                    ON push_alerts(created_at DESC, id DESC);

                CREATE TABLE IF NOT EXISTS push_alert_reads (
                    alert_id INTEGER NOT NULL,
                    installation_id TEXT NOT NULL,
                    read_at INTEGER NOT NULL,
                    PRIMARY KEY(alert_id, installation_id)
                );

                CREATE TABLE IF NOT EXISTS push_deliveries (
                    alert_id INTEGER NOT NULL,
                    installation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_code INTEGER,
                    message TEXT NOT NULL DEFAULT '',
                    attempted_at INTEGER NOT NULL,
                    PRIMARY KEY(alert_id, installation_id)
                );
                CREATE INDEX IF NOT EXISTS push_deliveries_attempted
                    ON push_deliveries(attempted_at DESC);
                """
            )
        _INITIALIZED = True


def _row_preferences(row: Any) -> DevicePreferences:
    return DevicePreferences(
        enabled=bool(row["enabled"]),
        xyft_enabled=bool(row["xyft_enabled"]),
        azxy10_enabled=bool(row["azxy10_enabled"]),
        ai_enabled=bool(row["ai_enabled"]),
        native_enabled=bool(row["native_enabled"]),
        escalation_enabled=bool(row["escalation_enabled"]),
    )


def _verify_device(installation_id: str, secret: str) -> dict[str, Any]:
    initialize()
    safe_id = installation_id.strip()
    safe_secret = secret.strip()
    if not safe_id or not safe_secret:
        raise PermissionError("缺少设备身份")
    with database.connection() as db:
        row = db.execute(
            "SELECT * FROM push_devices WHERE installation_id=?",
            (safe_id,),
        ).fetchone()
    if row is None or not hmac.compare_digest(
        str(row["secret_hash"]),
        _secret_hash(safe_secret),
    ):
        raise PermissionError("设备身份无效")
    return dict(row)


def register_device(
    *,
    installation_id: str,
    secret: str,
    fcm_token: str = "",
    platform: str = "android",
    app_version: str = "",
    device_name: str = "",
    preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    initialize()
    safe_id = installation_id.strip()[:128]
    safe_secret = secret.strip()
    if len(safe_id) < 8 or len(safe_secret) < 24:
        raise ValueError("设备标识或密钥格式无效")
    now = _now_ms()
    token = fcm_token.strip()[:4096]
    prefs = DevicePreferences.from_mapping(preferences)

    with database.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT secret_hash FROM push_devices WHERE installation_id=?",
            (safe_id,),
        ).fetchone()
        secret_digest = _secret_hash(safe_secret)
        if existing is not None and not hmac.compare_digest(
            str(existing["secret_hash"]),
            secret_digest,
        ):
            raise PermissionError("该设备标识已被其他密钥注册")
        if token:
            db.execute(
                """
                UPDATE push_devices
                SET fcm_token='', updated_at=?
                WHERE fcm_token=? AND installation_id<>?
                """,
                (now, token, safe_id),
            )
        db.execute(
            """
            INSERT INTO push_devices(
                installation_id,secret_hash,fcm_token,platform,app_version,device_name,
                enabled,xyft_enabled,azxy10_enabled,ai_enabled,native_enabled,
                escalation_enabled,created_at,updated_at,last_seen_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(installation_id) DO UPDATE SET
                fcm_token=excluded.fcm_token,
                platform=excluded.platform,
                app_version=excluded.app_version,
                device_name=excluded.device_name,
                enabled=excluded.enabled,
                xyft_enabled=excluded.xyft_enabled,
                azxy10_enabled=excluded.azxy10_enabled,
                ai_enabled=excluded.ai_enabled,
                native_enabled=excluded.native_enabled,
                escalation_enabled=excluded.escalation_enabled,
                updated_at=excluded.updated_at,
                last_seen_at=excluded.last_seen_at
            """,
            (
                safe_id,
                secret_digest,
                token,
                platform.strip()[:40] or "android",
                app_version.strip()[:80],
                device_name.strip()[:160],
                int(prefs.enabled),
                int(prefs.xyft_enabled),
                int(prefs.azxy10_enabled),
                int(prefs.ai_enabled),
                int(prefs.native_enabled),
                int(prefs.escalation_enabled),
                now,
                now,
                now,
            ),
        )
    return device_status(safe_id, safe_secret)


def update_preferences(
    installation_id: str,
    secret: str,
    preferences: dict[str, Any],
) -> dict[str, Any]:
    row = _verify_device(installation_id, secret)
    prefs = DevicePreferences.from_mapping(preferences)
    now = _now_ms()
    with database.connection() as db:
        db.execute(
            """
            UPDATE push_devices SET
                enabled=?,xyft_enabled=?,azxy10_enabled=?,ai_enabled=?,
                native_enabled=?,escalation_enabled=?,updated_at=?,last_seen_at=?
            WHERE installation_id=?
            """,
            (
                int(prefs.enabled),
                int(prefs.xyft_enabled),
                int(prefs.azxy10_enabled),
                int(prefs.ai_enabled),
                int(prefs.native_enabled),
                int(prefs.escalation_enabled),
                now,
                now,
                row["installation_id"],
            ),
        )
    return device_status(installation_id, secret)


def device_status(installation_id: str, secret: str) -> dict[str, Any]:
    row = _verify_device(installation_id, secret)
    prefs = _row_preferences(row)
    with database.connection() as db:
        unread = int(
            db.execute(
                """
                SELECT COUNT(*) FROM push_alerts a
                LEFT JOIN push_alert_reads r
                  ON r.alert_id=a.id AND r.installation_id=?
                WHERE r.alert_id IS NULL
                """,
                (installation_id,),
            ).fetchone()[0]
        )
    return {
        "installation_id": installation_id,
        "registered": True,
        "fcm_token_present": bool(row.get("fcm_token")),
        "push_configured": settings.fcm_enabled,
        "fallback_poll_minutes": 15,
        "unread_count": unread,
        "preferences": prefs.as_dict(),
        "updated_at_epoch_ms": int(row["updated_at"]),
    }


def list_alerts(
    installation_id: str,
    secret: str,
    *,
    limit: int = 100,
    after_id: int = 0,
) -> dict[str, Any]:
    _verify_device(installation_id, secret)
    safe_limit = max(1, min(200, int(limit)))
    safe_after = max(0, int(after_id))
    with database.connection() as db:
        rows = db.execute(
            """
            SELECT a.*, CASE WHEN r.alert_id IS NULL THEN 0 ELSE 1 END AS is_read
            FROM push_alerts a
            LEFT JOIN push_alert_reads r
              ON r.alert_id=a.id AND r.installation_id=?
            WHERE a.id>?
            ORDER BY a.id DESC
            LIMIT ?
            """,
            (installation_id, safe_after, safe_limit),
        ).fetchall()
        db.execute(
            "UPDATE push_devices SET last_seen_at=? WHERE installation_id=?",
            (_now_ms(), installation_id),
        )
    return {
        "items": [_alert_row(row) for row in rows],
        "push_configured": settings.fcm_enabled,
        "generated_at_epoch_ms": _now_ms(),
    }


def mark_alert_read(
    installation_id: str,
    secret: str,
    alert_id: int,
) -> dict[str, Any]:
    _verify_device(installation_id, secret)
    now = _now_ms()
    with database.connection() as db:
        exists = db.execute(
            "SELECT 1 FROM push_alerts WHERE id=?",
            (int(alert_id),),
        ).fetchone()
        if exists is None:
            raise LookupError("预警不存在")
        db.execute(
            """
            INSERT INTO push_alert_reads(alert_id,installation_id,read_at)
            VALUES(?,?,?)
            ON CONFLICT(alert_id,installation_id) DO UPDATE SET read_at=excluded.read_at
            """,
            (int(alert_id), installation_id, now),
        )
    return {"ok": True, "alert_id": int(alert_id), "read_at_epoch_ms": now}


def mark_all_read(installation_id: str, secret: str) -> dict[str, Any]:
    _verify_device(installation_id, secret)
    now = _now_ms()
    with database.connection() as db:
        rows = db.execute("SELECT id FROM push_alerts").fetchall()
        db.executemany(
            """
            INSERT INTO push_alert_reads(alert_id,installation_id,read_at)
            VALUES(?,?,?)
            ON CONFLICT(alert_id,installation_id) DO UPDATE SET read_at=excluded.read_at
            """,
            [(int(row["id"]), installation_id, now) for row in rows],
        )
    return {"ok": True, "read_at_epoch_ms": now, "count": len(rows)}


def _alert_row(row: Any) -> dict[str, Any]:
    recent = json.loads(str(row["recent_periods_json"]))
    data = json.loads(str(row["data_json"]))
    return {
        "id": int(row["id"]),
        "event_key": str(row["event_key"]),
        "lottery": str(row["lottery"]),
        "lottery_name": str(row["lottery_name"]),
        "source": str(row["source"]),
        "source_name": str(row["source_name"]),
        "model": str(row["model"]),
        "streak": int(row["streak"]),
        "threshold": int(row["threshold"]),
        "latest_target_period": str(row["latest_target_period"]),
        "recent_periods": recent,
        "title": str(row["title"]),
        "body": str(row["body"]),
        "data": data,
        "created_at_epoch_ms": int(row["created_at"]),
        "is_read": bool(row["is_read"]) if "is_read" in row.keys() else False,
    }


def _event_key(
    lottery: str,
    source: str,
    model: str,
    streak: int,
    latest_target_period: str,
) -> str:
    raw = f"{lottery}|{source}|{model}|{streak}|{latest_target_period}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def materialize_warning_alerts(
    watch: dict[str, Any],
    *,
    lottery_filter: str | None = None,
) -> list[int]:
    initialize()
    inserted_ids: list[int] = []
    prealert_threshold = PREALERT_THRESHOLD
    strong_threshold = max(STRONG_ALERT_THRESHOLD, int(settings.push_threshold))
    now = _now_ms()
    for lottery in watch.get("lotteries") or []:
        lottery_key = str(lottery.get("key") or "")
        if lottery_filter and lottery_key != lottery_filter:
            continue
        lottery_name = str(lottery.get("name") or lottery_key)
        for prediction in lottery.get("predictions") or []:
            if not bool(prediction.get("warning")):
                continue
            source = str(prediction.get("source") or "")
            model = str(prediction.get("model") or "")
            source_name = str(prediction.get("source_name") or source)
            streak = int(prediction.get("current_miss_streak") or 0)
            recent = list(prediction.get("recent_three") or [])
            latest_period = str(
                (recent[0].get("target_period") if recent else "")
                or prediction.get("latest_target_period")
                or ""
            )
            if (
                not lottery_key
                or not source
                or not model
                or streak < prealert_threshold
                or not latest_period
            ):
                continue
            event_key = _event_key(lottery_key, source, model, streak, latest_period)
            recent_periods = [
                str(item.get("target_period") or "")
                for item in recent[:strong_threshold]
                if str(item.get("target_period") or "")
            ]
            if streak == prealert_threshold:
                title = "两期不中预警"
                alert_level = "prealert"
            elif streak == strong_threshold:
                title = "三期不中加强提醒"
                alert_level = "strong"
            else:
                title = f"连续 {streak} 期不中升级预警"
                alert_level = "escalation"
            body = f"{lottery_name} · {source_name} · {model} 已连续 {streak} 期 Top 6 未命中"
            data = {
                "type": "prediction_miss_alert",
                "lottery": lottery_key,
                "lottery_name": lottery_name,
                "source": source,
                "source_name": source_name,
                "model": model,
                "streak": str(streak),
                "threshold": str(strong_threshold),
                "prealert_threshold": str(prealert_threshold),
                "alert_level": alert_level,
                "latest_target_period": latest_period,
                "recent_periods": ",".join(recent_periods),
            }
            with database.connection() as db:
                cursor = db.execute(
                    """
                    INSERT OR IGNORE INTO push_alerts(
                        event_key,lottery,lottery_name,source,source_name,model,
                        streak,threshold,latest_target_period,recent_periods_json,
                        title,body,data_json,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        event_key,
                        lottery_key,
                        lottery_name,
                        source,
                        source_name,
                        model,
                        streak,
                        strong_threshold,
                        latest_period,
                        json.dumps(recent_periods, ensure_ascii=False),
                        title,
                        body,
                        json.dumps(data, ensure_ascii=False),
                        now,
                    ),
                )
                if cursor.rowcount:
                    inserted_ids.append(int(cursor.lastrowid))
    return inserted_ids


def process_prediction_alerts(lottery_key: str | None = None) -> dict[str, Any]:
    watch = prediction_miss_watch(threshold=PREALERT_THRESHOLD)
    inserted = materialize_warning_alerts(watch, lottery_filter=lottery_key)
    delivery = deliver_pending_alerts(lottery_key)
    return {
        "created_alert_ids": inserted,
        "delivery": delivery,
        "push_configured": settings.fcm_enabled or settings.telegram_enabled,
        "channels": {
            "fcm": settings.fcm_enabled,
            "telegram": settings.telegram_enabled,
        },
    }


def _device_accepts(row: Any, alert: Any) -> bool:
    prefs = _row_preferences(row)
    if not prefs.enabled:
        return False
    lottery = str(alert["lottery"])
    source = str(alert["source"])
    streak = int(alert["streak"])
    threshold = int(alert["threshold"])
    if lottery == "xyft" and not prefs.xyft_enabled:
        return False
    if lottery == "azxy10" and not prefs.azxy10_enabled:
        return False
    if source == "ai" and not prefs.ai_enabled:
        return False
    if source == "native" and not prefs.native_enabled:
        return False
    if streak > threshold and not prefs.escalation_enabled:
        return False
    return True


def _credentials() -> service_account.Credentials | None:
    global _CREDENTIALS
    if not settings.fcm_enabled:
        return None
    with _CREDENTIAL_LOCK:
        if _CREDENTIALS is None:
            try:
                raw = base64.b64decode(settings.fcm_service_account_b64).decode("utf-8")
                info = json.loads(raw)
                _CREDENTIALS = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=["https://www.googleapis.com/auth/firebase.messaging"],
                )
            except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
                return None
        if not _CREDENTIALS.valid or _CREDENTIALS.expired:
            _CREDENTIALS.refresh(GoogleAuthRequest())
        return _CREDENTIALS


def _send_fcm(token: str, alert: Any) -> tuple[bool, int | None, str]:
    credentials = _credentials()
    if credentials is None or not credentials.token:
        return False, None, "FCM 尚未配置"
    data = json.loads(str(alert["data_json"]))
    data["alert_id"] = str(alert["id"])
    payload = {
        "message": {
            "token": token,
            "notification": {
                "title": str(alert["title"]),
                "body": str(alert["body"]),
            },
            "data": {str(key): str(value) for key, value in data.items()},
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": CHANNEL_ID,
                    "default_sound": True,
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
        message = response.text[:800]
        return response.ok, int(response.status_code), message
    except requests.RequestException as exc:
        return False, None, str(exc)[:800]


def _delivery_allowed(
    deliveries: dict[tuple[int, str], dict[str, Any]],
    *,
    alert_id: int,
    target_key: str,
    retry_before: int,
) -> bool:
    previous = deliveries.get((alert_id, target_key))
    if previous and previous["status"] == "sent":
        return False
    if previous and int(previous["attempted_at"]) > retry_before:
        return False
    return True



def _claim_delivery(
    *,
    alert_id: int,
    target_key: str,
    attempted_at: int,
    retry_before: int,
) -> bool:
    """Atomically reserve one alert/target delivery across concurrent cycles."""
    with database.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute(
            """
            SELECT status,attempted_at
            FROM push_deliveries
            WHERE alert_id=? AND installation_id=?
            """,
            (alert_id, target_key),
        ).fetchone()
        if previous is not None:
            if str(previous["status"]) == "sent":
                return False
            if int(previous["attempted_at"]) > retry_before:
                return False
        db.execute(
            """
            INSERT INTO push_deliveries(
                alert_id,installation_id,status,response_code,message,attempted_at
            ) VALUES(?,?,'sending',NULL,'',?)
            ON CONFLICT(alert_id,installation_id) DO UPDATE SET
                status='sending',response_code=NULL,message='',attempted_at=excluded.attempted_at
            """,
            (alert_id, target_key, attempted_at),
        )
    return True

def _store_delivery(
    *,
    alert_id: int,
    target_key: str,
    ok: bool,
    code: int | None,
    message: str,
    attempted_at: int,
) -> None:
    with database.connection() as db:
        db.execute(
            """
            INSERT INTO push_deliveries(
                alert_id,installation_id,status,response_code,message,attempted_at
            ) VALUES(?,?,?,?,?,?)
            ON CONFLICT(alert_id,installation_id) DO UPDATE SET
                status=excluded.status,
                response_code=excluded.response_code,
                message=excluded.message,
                attempted_at=excluded.attempted_at
            """,
            (
                alert_id,
                target_key,
                "sent" if ok else "failed",
                code,
                message,
                attempted_at,
            ),
        )


def deliver_pending_alerts(lottery_filter: str | None = None) -> dict[str, int]:
    initialize()
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

    now = _now_ms()
    retry_before = now - 300_000
    with database.connection() as db:
        if lottery_filter:
            alerts = db.execute(
                "SELECT * FROM push_alerts WHERE lottery=? ORDER BY id DESC LIMIT 100",
                (lottery_filter,),
            ).fetchall()
        else:
            alerts = db.execute(
                "SELECT * FROM push_alerts ORDER BY id DESC LIMIT 100"
            ).fetchall()
        devices = (
            db.execute(
                "SELECT * FROM push_devices WHERE fcm_token<>'' ORDER BY updated_at DESC"
            ).fetchall()
            if settings.fcm_enabled
            else []
        )

    fcm_sent = fcm_failed = telegram_sent = telegram_failed = skipped = 0

    if settings.fcm_enabled:
        for alert in alerts:
            alert_id = int(alert["id"])
            for device in devices:
                if not _device_accepts(device, alert):
                    skipped += 1
                    continue
                target_key = str(device["installation_id"])
                if not _claim_delivery(
                    alert_id=alert_id,
                    target_key=target_key,
                    attempted_at=now,
                    retry_before=retry_before,
                ):
                    continue
                ok, code, message = _send_fcm(str(device["fcm_token"]), alert)
                _store_delivery(
                    alert_id=alert_id,
                    target_key=target_key,
                    ok=ok,
                    code=code,
                    message=message,
                    attempted_at=now,
                )
                if not ok and code in {400, 404} and (
                    "UNREGISTERED" in message
                    or "registration-token-not-registered" in message
                ):
                    with database.connection() as db:
                        db.execute(
                            "UPDATE push_devices SET fcm_token='',updated_at=? WHERE installation_id=?",
                            (now, target_key),
                        )
                if ok:
                    fcm_sent += 1
                else:
                    fcm_failed += 1

    if settings.telegram_enabled:
        for alert in alerts:
            alert_id = int(alert["id"])
            for chat_id in settings.telegram_chat_ids:
                target_key = telegram_alerts.delivery_key(chat_id)
                if not _claim_delivery(
                    alert_id=alert_id,
                    target_key=target_key,
                    attempted_at=now,
                    retry_before=retry_before,
                ):
                    continue
                ok, code, message = telegram_alerts.send_alert(
                    bot_token=settings.telegram_bot_token,
                    chat_id=chat_id,
                    alert=alert,
                )
                _store_delivery(
                    alert_id=alert_id,
                    target_key=target_key,
                    ok=ok,
                    code=code,
                    message=message,
                    attempted_at=now,
                )
                if ok:
                    telegram_sent += 1
                else:
                    telegram_failed += 1

    sent = fcm_sent + telegram_sent
    failed = fcm_failed + telegram_failed
    return {
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "fcm_sent": fcm_sent,
        "fcm_failed": fcm_failed,
        "telegram_sent": telegram_sent,
        "telegram_failed": telegram_failed,
    }
