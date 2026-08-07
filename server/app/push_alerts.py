from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import hmac
import html
import json
import re
import threading
import time
from typing import Any

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from .admin_insights import prediction_miss_watch
from .config import settings
from .db import database
from .lottery import parse_epoch_ms
from .migrations import run_migrations
from . import telegram_alerts


CHANNEL_ID = "tianji_prediction_alerts"
NORMAL_CHANNEL_ID = "tianji_prediction_updates"
PREALERT_THRESHOLD = 2
STRONG_ALERT_THRESHOLD = 3
PROTOCOL_VERSION = 2
DELIVERY_WINDOW_MS = 72 * 60 * 60 * 1000
PREDICTION_EXPIRY_MS = 6 * 60 * 60 * 1000
ALERT_EXPIRY_MS = 72 * 60 * 60 * 1000
WARNING_SETTLEMENT_FRESH_MS = 20 * 60 * 1000
WARNING_ALERT_FRESH_MS = 30 * 60 * 1000
WARNING_DRAW_FRESH_MS = 60 * 60 * 1000
WARNING_EVENT_TYPES = {"miss_prealert", "miss_alert", "miss_escalation"}

_INIT_LOCK = threading.Lock()
_INITIALIZED = False
_CREDENTIAL_LOCK = threading.Lock()
_CREDENTIALS: service_account.Credentials | None = None
_DELIVERY_STATE_LOCK = threading.Lock()
_DELIVERY_BATCH_RUNNING = False
_DELIVERY_BATCH_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tianji-push-batch")
_DELIVERY_CHANNEL_EXECUTOR = ThreadPoolExecutor(
    max_workers=max(4, settings.push_delivery_workers + max(1, len(settings.telegram_chat_ids))),
    thread_name_prefix="tianji-push-channel",
)


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
        run_migrations()
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
    secret_digest = _secret_hash(safe_secret)

    with database.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT secret_hash FROM push_devices WHERE installation_id=?",
            (safe_id,),
        ).fetchone()
        if existing is not None and not hmac.compare_digest(
            str(existing["secret_hash"]),
            secret_digest,
        ):
            raise PermissionError("该设备标识已被其他密钥注册")
        if token:
            db.execute(
                "UPDATE push_devices SET fcm_token='',updated_at=? WHERE fcm_token=? AND installation_id<>?",
                (now, token, safe_id),
            )
        db.execute(
            """
            INSERT INTO push_devices(
                installation_id,secret_hash,fcm_token,platform,app_version,device_name,
                enabled,xyft_enabled,azxy10_enabled,ai_enabled,native_enabled,
                escalation_enabled,created_at,updated_at,last_seen_at,
                read_through_alert_id,protocol_version
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                protocol_version=2,
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
                0,
                PROTOCOL_VERSION,
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
                enabled=?,xyft_enabled=?,azxy10_enabled=?,ai_enabled=?,native_enabled=?,
                escalation_enabled=?,protocol_version=2,updated_at=?,last_seen_at=?
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
    cursor = int(row.get("read_through_alert_id") or 0)
    with database.connection() as db:
        unread = int(
            db.execute(
                """
                SELECT COUNT(*) FROM push_alerts AS a
                LEFT JOIN push_alert_reads AS r
                  ON r.alert_id=a.id AND r.installation_id=?
                WHERE a.id>? AND r.alert_id IS NULL
                  AND (a.expires_at IS NULL OR a.expires_at>?)
                """,
                (installation_id, cursor, _now_ms()),
            ).fetchone()[0]
        )
    return {
        "installation_id": installation_id,
        "registered": True,
        "protocol_version": PROTOCOL_VERSION,
        "fcm_token_present": bool(row.get("fcm_token")),
        "push_configured": settings.fcm_enabled,
        "fallback_poll_minutes": 15,
        "unread_count": unread,
        "read_through_alert_id": cursor,
        "preferences": prefs.as_dict(),
        "updated_at_epoch_ms": int(row["updated_at"]),
    }


def _event_metadata(row: Any) -> dict[str, Any]:
    try:
        data = json.loads(str(row["data_json"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    keys = row.keys() if hasattr(row, "keys") else row
    event_type = str(row["event_type"] if "event_type" in keys else "") or str(
        data.get("event_type") or "miss_alert"
    )
    severity = str(row["severity"] if "severity" in keys else "") or str(
        data.get("severity") or "warning"
    )
    created_at = int(row["created_at"])
    raw_expiry = row["expires_at"] if "expires_at" in keys else None
    expires_at = int(raw_expiry) if raw_expiry is not None else created_at + (
        PREDICTION_EXPIRY_MS if event_type == "prediction_ready" else ALERT_EXPIRY_MS
    )
    raw_collapse = row["collapse_key"] if "collapse_key" in keys else ""
    collapse_key = str(
        raw_collapse
        or data.get("collapse_key")
        or f"{row['lottery']}:{row['source']}:{row['model']}"
    )[:160]
    raw_link = row["deep_link"] if "deep_link" in keys else ""
    deep_link = str(
        raw_link or data.get("deep_link") or f"tianji://alerts/{int(row['id'])}"
    )[:500]
    return {
        "data": data,
        "event_type": event_type,
        "severity": severity,
        "expires_at": expires_at,
        "collapse_key": collapse_key,
        "deep_link": deep_link,
    }


def _alert_row(row: Any) -> dict[str, Any]:
    metadata = _event_metadata(row)
    try:
        recent = json.loads(str(row["recent_periods_json"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        recent = []
    if not isinstance(recent, list):
        recent = []
    keys = row.keys() if hasattr(row, "keys") else row
    schema_version = int(row["schema_version"] if "schema_version" in keys else PROTOCOL_VERSION)
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
        "recent_periods": [str(value) for value in recent],
        "title": str(row["title"]),
        "body": str(row["body"]),
        "data": metadata["data"],
        "created_at_epoch_ms": int(row["created_at"]),
        "schema_version": schema_version,
        "event_type": metadata["event_type"],
        "severity": metadata["severity"],
        "deep_link": metadata["deep_link"],
        "collapse_key": metadata["collapse_key"],
        "expires_at_epoch_ms": metadata["expires_at"],
        "is_read": bool(row["is_read"]) if "is_read" in keys else False,
    }


def list_alerts(
    installation_id: str,
    secret: str,
    *,
    limit: int = 100,
    after_id: int = 0,
) -> dict[str, Any]:
    row = _verify_device(installation_id, secret)
    cursor = int(row.get("read_through_alert_id") or 0)
    safe_limit = max(1, min(200, int(limit)))
    safe_after = max(0, int(after_id))
    order = "ASC" if safe_after > 0 else "DESC"
    now = _now_ms()
    with database.connection() as db:
        rows = db.execute(
            f"""
            SELECT a.*,
                CASE WHEN a.id<=? OR r.alert_id IS NOT NULL THEN 1 ELSE 0 END AS is_read
            FROM push_alerts AS a
            LEFT JOIN push_alert_reads AS r
              ON r.alert_id=a.id AND r.installation_id=?
            WHERE a.id>?
              AND (a.expires_at IS NULL OR a.expires_at>?)
            ORDER BY a.id {order}
            LIMIT ?
            """,
            (cursor, installation_id, safe_after, now, safe_limit),
        ).fetchall()
        db.execute(
            "UPDATE push_devices SET last_seen_at=?,protocol_version=2 WHERE installation_id=?",
            (now, installation_id),
        )
    return {
        "items": [_alert_row(value) for value in rows],
        "protocol_version": PROTOCOL_VERSION,
        "push_configured": settings.fcm_enabled,
        "generated_at_epoch_ms": now,
    }


def mark_alert_read(
    installation_id: str,
    secret: str,
    alert_id: int,
) -> dict[str, Any]:
    _verify_device(installation_id, secret)
    now = _now_ms()
    with database.connection() as db:
        exists = db.execute("SELECT 1 FROM push_alerts WHERE id=?", (int(alert_id),)).fetchone()
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
        latest = int(db.execute("SELECT COALESCE(MAX(id),0) FROM push_alerts").fetchone()[0])
        db.execute(
            """
            UPDATE push_devices
            SET read_through_alert_id=MAX(read_through_alert_id,?),updated_at=?,last_seen_at=?
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
            if not lottery_key or not source or not model or streak < prealert_threshold or not latest_period:
                continue
            event_key = _event_key(lottery_key, source, model, streak, latest_period)
            recent_periods = [
                str(item.get("target_period") or "")
                for item in recent[:strong_threshold]
                if str(item.get("target_period") or "")
            ]
            if streak == prealert_threshold:
                title = "两期不中预警"
                event_type = "miss_prealert"
                severity = "info"
            elif streak == strong_threshold:
                title = "三期不中加强提醒"
                event_type = "miss_alert"
                severity = "warning"
            else:
                title = f"连续 {streak} 期不中升级预警"
                event_type = "miss_escalation"
                severity = "critical"
            body = f"{lottery_name} · {source_name} · {model} 已连续 {streak} 期 Top 6 未命中"
            collapse_key = f"{lottery_key}:{source}:{model}"
            expires_at = now + ALERT_EXPIRY_MS
            data = {
                "type": "prediction_miss_alert",
                "schema_version": "2",
                "event_type": event_type,
                "severity": severity,
                "lottery": lottery_key,
                "lottery_name": lottery_name,
                "source": source,
                "source_name": source_name,
                "model": model,
                "streak": str(streak),
                "threshold": str(strong_threshold),
                "prealert_threshold": str(prealert_threshold),
                "latest_target_period": latest_period,
                "recent_periods": ",".join(recent_periods),
                "title": title,
                "body": body,
                "deep_link": "tianji://alerts",
                "collapse_key": collapse_key,
                "expires_at_epoch_ms": str(expires_at),
            }
            with database.connection() as db:
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
                        PROTOCOL_VERSION,
                        event_type,
                        severity,
                        "tianji://alerts",
                        collapse_key,
                        expires_at,
                    ),
                )
                if cursor.rowcount:
                    inserted_ids.append(int(cursor.lastrowid))
    return inserted_ids


def _plain_text(message_html: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", message_html, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return " · ".join(lines[:5])[:500]


def _mirror_telegram_events(lottery_filter: str | None = None) -> list[int]:
    params: list[Any] = [_now_ms() - 7 * 86_400_000]
    lottery_sql = ""
    if lottery_filter:
        lottery_sql = " AND lottery=?"
        params.append(lottery_filter)
    try:
        with database.connection() as db:
            rows = db.execute(
                f"""
                SELECT event_key,event_type,lottery,source,model,target_period,message_html,created_at
                FROM telegram_events
                WHERE created_at>=?{lottery_sql}
                ORDER BY created_at DESC
                LIMIT 1000
                """,
                tuple(params),
            ).fetchall()
    except Exception:
        return []

    inserted: list[int] = []
    with database.connection() as db:
        for row in rows:
            source_event = str(row["event_type"])
            if source_event == "prediction":
                event_type = "prediction_ready"
                severity = "info"
                title = "新一期云端 AI 预测"
                expiry = int(row["created_at"]) + PREDICTION_EXPIRY_MS
            elif source_event == "win":
                event_type = "hit_recovery"
                severity = "success"
                title = "连续不中后恢复命中"
                expiry = int(row["created_at"]) + ALERT_EXPIRY_MS
            else:
                continue
            body = _plain_text(str(row["message_html"]))
            event_key = f"unified:{row['event_key']}"
            lottery = str(row["lottery"])
            source = str(row["source"])
            model = str(row["model"])
            target_period = str(row["target_period"])
            source_name = "天机云端 AI" if source == "ai" else source
            collapse_key = f"{lottery}:{source}:{model}"
            data = {
                "schema_version": "2",
                "event_type": event_type,
                "severity": severity,
                "lottery": lottery,
                "lottery_name": lottery,
                "source": source,
                "source_name": source_name,
                "model": model,
                "latest_target_period": target_period,
                "title": title,
                "body": body,
                "deep_link": "tianji://alerts",
                "collapse_key": collapse_key,
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
                    source_name,
                    model,
                    0,
                    max(3, int(settings.push_threshold)),
                    target_period,
                    json.dumps([target_period], ensure_ascii=False),
                    title,
                    body,
                    json.dumps(data, ensure_ascii=False),
                    int(row["created_at"]),
                    PROTOCOL_VERSION,
                    event_type,
                    severity,
                    "tianji://alerts",
                    collapse_key,
                    expiry,
                ),
            )
            if cursor.rowcount:
                inserted.append(int(cursor.lastrowid))
    return inserted


def _latest_period_map() -> dict[str, str]:
    with database.connection() as db:
        rows = db.execute(
            """
            SELECT d.lottery,d.period
            FROM draws AS d
            WHERE d.period=(
                SELECT d2.period FROM draws AS d2
                WHERE d2.lottery=d.lottery
                ORDER BY LENGTH(d2.period) DESC,d2.period DESC
                LIMIT 1
            )
            """
        ).fetchall()
    return {str(row["lottery"]): str(row["period"]) for row in rows}


def _warning_candidate_is_fresh(
    *,
    target_period: str,
    latest_period: str,
    settled_at: int | None,
    draw_time: str,
    created_at: int | None,
    now_ms: int,
) -> bool:
    if not target_period or target_period != latest_period:
        return False
    if settled_at is None or created_at is None:
        return False
    if settled_at > now_ms or now_ms - settled_at > WARNING_SETTLEMENT_FRESH_MS:
        return False
    if created_at > now_ms or now_ms - created_at > WARNING_ALERT_FRESH_MS:
        return False
    draw_at = parse_epoch_ms(draw_time)
    if draw_at is None:
        return False
    draw_age = now_ms - draw_at
    return 0 <= draw_age <= WARNING_DRAW_FRESH_MS


def _prediction_target_period(prediction: dict[str, Any]) -> str:
    recent = list(prediction.get("recent_three") or [])
    if recent:
        value = str(recent[0].get("target_period") or "")
        if value:
            return value
    return str(prediction.get("latest_target_period") or "")


def _filter_watch_for_fresh_settlements(watch: dict[str, Any]) -> dict[str, Any]:
    now = _now_ms()
    latest_periods = _latest_period_map()
    lotteries_out: list[dict[str, Any]] = []
    warning_count = 0
    for lottery_value in list(watch.get("lotteries") or []):
        lottery = dict(lottery_value)
        lottery_key = str(lottery.get("key") or "")
        latest_period = latest_periods.get(lottery_key, "")
        predictions_out: list[dict[str, Any]] = []
        for prediction_value in list(lottery.get("predictions") or []):
            prediction = dict(prediction_value)
            if bool(prediction.get("warning")):
                target_period = _prediction_target_period(prediction)
                source = str(prediction.get("source") or "")
                model = str(prediction.get("model") or "")
                fresh = False
                if target_period and source and model and latest_period:
                    with database.connection() as db:
                        row = db.execute(
                            """
                            SELECT f.settled_at,d.draw_time
                            FROM forecasts AS f
                            LEFT JOIN draws AS d
                              ON d.lottery=f.lottery AND d.period=f.target_period
                            WHERE f.lottery=? AND f.source=? AND f.model=? AND f.target_period=?
                            ORDER BY f.id DESC LIMIT 1
                            """,
                            (lottery_key, source, model, target_period),
                        ).fetchone()
                    if row is not None:
                        fresh = _warning_candidate_is_fresh(
                            target_period=target_period,
                            latest_period=latest_period,
                            settled_at=None if row["settled_at"] is None else int(row["settled_at"]),
                            draw_time=str(row["draw_time"] or ""),
                            created_at=now,
                            now_ms=now,
                        )
                prediction["warning"] = fresh
                if fresh:
                    warning_count += 1
            predictions_out.append(prediction)
        lottery["predictions"] = predictions_out
        lottery["warning_count"] = sum(1 for item in predictions_out if bool(item.get("warning")))
        lotteries_out.append(lottery)
    result = dict(watch)
    result["warning_count"] = warning_count
    result["lotteries"] = lotteries_out
    result["generated_at_epoch_ms"] = now
    return result


def _expire_invalid_warning_alerts() -> None:
    now = _now_ms()
    latest_periods = _latest_period_map()
    placeholders = ",".join("?" for _ in WARNING_EVENT_TYPES)
    with database.connection() as db:
        rows = db.execute(
            f"""
            SELECT a.id,a.collapse_key,a.lottery,a.latest_target_period,a.created_at,
                   f.settled_at,d.draw_time
            FROM push_alerts AS a
            LEFT JOIN forecasts AS f
              ON f.lottery=a.lottery AND f.source=a.source AND f.model=a.model
             AND f.target_period=a.latest_target_period
            LEFT JOIN draws AS d
              ON d.lottery=a.lottery AND d.period=a.latest_target_period
            WHERE a.event_type IN ({placeholders})
              AND (a.expires_at IS NULL OR a.expires_at>?)
            ORDER BY a.id DESC
            """,
            (*sorted(WARNING_EVENT_TYPES), now),
        ).fetchall()
        invalid_ids: list[int] = []
        seen: set[str] = set()
        for row in rows:
            collapse = str(row["collapse_key"] or row["lottery"])
            if collapse in seen:
                invalid_ids.append(int(row["id"]))
                continue
            seen.add(collapse)
            if not _warning_candidate_is_fresh(
                target_period=str(row["latest_target_period"] or ""),
                latest_period=latest_periods.get(str(row["lottery"]), ""),
                settled_at=None if row["settled_at"] is None else int(row["settled_at"]),
                draw_time=str(row["draw_time"] or ""),
                created_at=int(row["created_at"]),
                now_ms=now,
            ):
                invalid_ids.append(int(row["id"]))
        if invalid_ids:
            marks = ",".join("?" for _ in invalid_ids)
            db.execute(
                f"UPDATE push_alerts SET expires_at=? WHERE id IN ({marks})",
                (now, *invalid_ids),
            )


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


def _message_data(alert: Any) -> dict[str, str]:
    metadata = _event_metadata(alert)
    try:
        recent = json.loads(str(alert["recent_periods_json"] or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        recent = []
    if not isinstance(recent, list):
        recent = []
    data = dict(metadata["data"])
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
            "schema_version": str(PROTOCOL_VERSION),
            "event_type": metadata["event_type"],
            "severity": metadata["severity"],
            "deep_link": metadata["deep_link"],
            "collapse_key": metadata["collapse_key"],
            "expires_at_epoch_ms": str(metadata["expires_at"]),
        }
    )
    return {str(key): str(value) for key, value in data.items()}


def _send_fcm(token: str, alert: Any) -> tuple[bool, int | None, str]:
    credentials = _credentials()
    if credentials is None or not credentials.token:
        return False, None, "FCM 尚未配置"
    data = _message_data(alert)
    severity = data.get("severity", "info")
    ttl_seconds = max(
        60,
        min(259_200, (int(data["expires_at_epoch_ms"]) - _now_ms()) // 1000),
    )
    payload = {
        "message": {
            "token": token,
            # Data-only is intentional: TianjiMessagingService owns local channel selection,
            # deduplication and deep-link behavior in foreground and background delivery.
            "data": data,
            "android": {
                "priority": "HIGH" if severity in {"warning", "critical"} else "NORMAL",
                "ttl": f"{ttl_seconds}s",
                "collapse_key": data.get("collapse_key", "tianji_general")[:64],
                "direct_boot_ok": False,
            },
        }
    }
    url = f"https://fcm.googleapis.com/v1/projects/{settings.fcm_project_id}/messages:send"
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json=payload,
            timeout=6,
        )
        return response.ok, int(response.status_code), response.text[:800]
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
    initialize()
    with database.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute(
            "SELECT status,attempted_at FROM push_deliveries WHERE alert_id=? AND installation_id=?",
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
                status=excluded.status,response_code=excluded.response_code,
                message=excluded.message,attempted_at=excluded.attempted_at
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


def _device_accepts(row: Any, alert: Any) -> bool:
    prefs = _row_preferences(row)
    if not prefs.enabled:
        return False
    lottery = str(alert["lottery"])
    source = str(alert["source"])
    event_type = str(alert["event_type"] or "")
    if lottery == "xyft" and not prefs.xyft_enabled:
        return False
    if lottery == "azxy10" and not prefs.azxy10_enabled:
        return False
    if source == "ai" and not prefs.ai_enabled:
        return False
    if source == "native" and not prefs.native_enabled:
        return False
    if event_type == "miss_escalation" and not prefs.escalation_enabled:
        return False
    return True


def _load_delivery_candidates() -> tuple[list[Any], list[Any]]:
    _expire_invalid_warning_alerts()
    now = _now_ms()
    retry_before = now - max(60, settings.push_retry_seconds) * 1000
    lower_bound = now - DELIVERY_WINDOW_MS
    with database.connection() as db:
        alerts = db.execute(
            """
            SELECT * FROM push_alerts
            WHERE created_at>=? AND (expires_at IS NULL OR expires_at>?)
            ORDER BY id DESC LIMIT 200
            """,
            (lower_bound, now),
        ).fetchall()
        devices = db.execute(
            "SELECT * FROM push_devices WHERE enabled=1 AND fcm_token<>'' ORDER BY updated_at DESC"
        ).fetchall()
    return list(alerts), list(devices)


def _deliver_fcm_one(alert: Any, device: Any, retry_before: int) -> tuple[str, bool]:
    target_key = str(device["installation_id"])
    if not _device_accepts(device, alert):
        return "skipped", False
    attempted = _now_ms()
    if not _claim_delivery(
        alert_id=int(alert["id"]),
        target_key=target_key,
        attempted_at=attempted,
        retry_before=retry_before,
    ):
        return "duplicate", False
    ok, code, message = _send_fcm(str(device["fcm_token"]), alert)
    _store_delivery(
        alert_id=int(alert["id"]),
        target_key=target_key,
        ok=ok,
        code=code,
        message=message,
        attempted_at=attempted,
    )
    if not ok and code in {400, 404} and (
        "UNREGISTERED" in message or "registration-token-not-registered" in message
    ):
        with database.connection() as db:
            db.execute(
                "UPDATE push_devices SET fcm_token='',updated_at=? WHERE installation_id=?",
                (_now_ms(), target_key),
            )
    return "sent" if ok else "failed", ok


def _deliver_telegram_one(alert: Any, chat_id: str, retry_before: int) -> tuple[str, bool]:
    # prediction_ready/hit_recovery are already sent by telegram_events; they are mirrored here
    # only for App history and FCM.
    if str(alert["event_type"] or "") in {"prediction_ready", "hit_recovery"}:
        return "skipped", False
    target_key = telegram_alerts.delivery_key(chat_id)
    attempted = _now_ms()
    if not _claim_delivery(
        alert_id=int(alert["id"]),
        target_key=target_key,
        attempted_at=attempted,
        retry_before=retry_before,
    ):
        return "duplicate", False
    ok, code, message = telegram_alerts.send_alert(
        bot_token=settings.telegram_bot_token,
        chat_id=chat_id,
        alert=alert,
        timeout_seconds=6,
    )
    _store_delivery(
        alert_id=int(alert["id"]),
        target_key=target_key,
        ok=ok,
        code=code,
        message=message,
        attempted_at=attempted,
    )
    return "sent" if ok else "failed", ok


def _run_delivery_batch() -> dict[str, int]:
    global _DELIVERY_BATCH_RUNNING
    sent = failed = skipped = 0
    fcm_sent = fcm_failed = telegram_sent = telegram_failed = 0
    try:
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
        alerts, devices = _load_delivery_candidates()
        retry_before = _now_ms() - max(60, settings.push_retry_seconds) * 1000
        futures = []

        # Telegram warning tasks are submitted first. FCM fans out immediately afterwards on the
        # same channel pool, so neither transport can serially block the other.
        if settings.telegram_enabled:
            for alert in alerts:
                for chat_id in settings.telegram_chat_ids:
                    futures.append(
                        ("telegram", _DELIVERY_CHANNEL_EXECUTOR.submit(
                            _deliver_telegram_one,
                            alert,
                            chat_id,
                            retry_before,
                        ))
                    )
        if settings.fcm_enabled:
            for alert in alerts:
                for device in devices:
                    futures.append(
                        ("fcm", _DELIVERY_CHANNEL_EXECUTOR.submit(
                            _deliver_fcm_one,
                            alert,
                            device,
                            retry_before,
                        ))
                    )

        for channel, future in futures:
            try:
                status, ok = future.result()
            except Exception:
                status, ok = "failed", False
            if status in {"skipped", "duplicate"}:
                skipped += 1
                continue
            if ok:
                sent += 1
                if channel == "fcm":
                    fcm_sent += 1
                else:
                    telegram_sent += 1
            else:
                failed += 1
                if channel == "fcm":
                    fcm_failed += 1
                else:
                    telegram_failed += 1
        result = {
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "fcm_sent": fcm_sent,
            "fcm_failed": fcm_failed,
            "telegram_sent": telegram_sent,
            "telegram_failed": telegram_failed,
        }
        database.set_state(
            "push_delivery_last",
            json.dumps({**result, "completed_at_epoch_ms": _now_ms()}, ensure_ascii=False),
        )
        return result
    finally:
        with _DELIVERY_STATE_LOCK:
            _DELIVERY_BATCH_RUNNING = False


def deliver_pending_alerts(lottery_filter: str | None = None) -> dict[str, int]:
    """Queue one delivery pass and return immediately.

    `lottery_filter` is retained for API compatibility. Delivery intentionally scans all pending
    non-expired alerts so concurrent lottery cycles coalesce into one batch instead of starving the
    second lottery behind a per-filter in-flight lock.
    """
    del lottery_filter
    global _DELIVERY_BATCH_RUNNING
    initialize()
    with _DELIVERY_STATE_LOCK:
        if _DELIVERY_BATCH_RUNNING:
            return {
                "sent": 0,
                "failed": 0,
                "skipped": 0,
                "queued": 0,
                "in_flight": 1,
            }
        _DELIVERY_BATCH_RUNNING = True
        _DELIVERY_BATCH_EXECUTOR.submit(_run_delivery_batch)
    return {
        "sent": 0,
        "failed": 0,
        "skipped": 0,
        "queued": 1,
        "in_flight": 1,
    }


def process_prediction_alerts(lottery_key: str | None = None) -> dict[str, Any]:
    initialize()
    watch = prediction_miss_watch(threshold=PREALERT_THRESHOLD)
    filtered = _filter_watch_for_fresh_settlements(watch)
    warning_ids = materialize_warning_alerts(filtered, lottery_filter=lottery_key)
    mirrored_ids = _mirror_telegram_events(lottery_key)
    delivery = deliver_pending_alerts()
    return {
        "created_alert_ids": warning_ids + mirrored_ids,
        "delivery": delivery,
        "protocol_version": PROTOCOL_VERSION,
        "push_configured": settings.fcm_enabled or settings.telegram_enabled,
        "channels": {
            "fcm": settings.fcm_enabled,
            "telegram": settings.telegram_enabled,
        },
    }
