from __future__ import annotations

import html
import json
import threading
import time
from typing import Any

from . import telegram_alerts
from .config import settings
from .db import database
from .models import LOTTERIES


_INIT_LOCK = threading.Lock()
_INITIALIZED = False
_BASELINE_KEY = "telegram_events_baseline_ms"
_PREDICTION_POLICY_KEY = "telegram_prediction_policy_always_v3"
_PREDICTION_START_KEY = "telegram_prediction_always_from_ms_v1"
_WIN_POLICY_KEY = "telegram_win_policy_tracking_only_v1"
_STRONG_ALERT_AFTER_MISSES = 3
_MAX_PENDING_PER_TARGET = 24
_MAX_PREDICTION_EVENT_AGE_MS = 8 * 60_000
_RETRY_COOLDOWN_MS = 60_000


def _now_ms() -> int:
    return int(time.time() * 1000)


def initialize() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    with _INIT_LOCK:
        if _INITIALIZED:
            return
        now = _now_ms()
        with database.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS telegram_events (
                    event_key TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    lottery TEXT NOT NULL,
                    source TEXT NOT NULL,
                    model TEXT NOT NULL,
                    target_period TEXT NOT NULL,
                    message_html TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS telegram_events_created
                    ON telegram_events(created_at DESC);

                CREATE TABLE IF NOT EXISTS telegram_event_deliveries (
                    event_key TEXT NOT NULL,
                    target_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_code INTEGER,
                    message TEXT NOT NULL DEFAULT '',
                    attempted_at INTEGER NOT NULL,
                    PRIMARY KEY(event_key, target_key)
                );
                CREATE INDEX IF NOT EXISTS telegram_event_deliveries_attempted
                    ON telegram_event_deliveries(attempted_at DESC);

                CREATE TABLE IF NOT EXISTS telegram_event_state (
                    state_key TEXT PRIMARY KEY,
                    state_value TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                """
            )
            db.execute(
                """
                INSERT OR IGNORE INTO telegram_event_state(
                    state_key,state_value,updated_at
                ) VALUES(?,?,?)
                """,
                (_BASELINE_KEY, str(now), now),
            )

            prediction_policy = db.execute(
                "SELECT 1 FROM telegram_event_state WHERE state_key=?",
                (_PREDICTION_POLICY_KEY,),
            ).fetchone()
            if prediction_policy is None:
                # 新策略从服务器升级完成后开始，不补发旧预测，避免历史消息轰炸。
                db.execute(
                    """
                    DELETE FROM telegram_events
                    WHERE event_type='prediction'
                      AND NOT EXISTS (
                          SELECT 1 FROM telegram_event_deliveries AS delivery
                          WHERE delivery.event_key=telegram_events.event_key
                            AND delivery.status='sent'
                      )
                    """
                )
                db.execute(
                    """
                    INSERT INTO telegram_event_state(
                        state_key,state_value,updated_at
                    ) VALUES(?,?,?)
                    """,
                    (_PREDICTION_POLICY_KEY, "always_push_cloud_ai", now),
                )
                db.execute(
                    """
                    INSERT INTO telegram_event_state(
                        state_key,state_value,updated_at
                    ) VALUES(?,?,?)
                    ON CONFLICT(state_key) DO UPDATE SET
                        state_value=excluded.state_value,
                        updated_at=excluded.updated_at
                    """,
                    (_PREDICTION_START_KEY, str(now), now),
                )

            win_policy = db.execute(
                "SELECT 1 FROM telegram_event_state WHERE state_key=?",
                (_WIN_POLICY_KEY,),
            ).fetchone()
            if win_policy is None:
                # 普通中奖保持静默，只保留连续三期不中后的恢复命中消息。
                db.execute(
                    """
                    DELETE FROM telegram_events
                    WHERE event_type='win'
                      AND NOT EXISTS (
                          SELECT 1 FROM telegram_event_deliveries AS delivery
                          WHERE delivery.event_key=telegram_events.event_key
                            AND delivery.status='sent'
                      )
                    """
                )
                db.execute(
                    """
                    INSERT INTO telegram_event_state(
                        state_key,state_value,updated_at
                    ) VALUES(?,?,?)
                    """,
                    (_WIN_POLICY_KEY, "recovery_after_three_misses_only", now),
                )
        _INITIALIZED = True


def _state_ms(state_key: str, fallback: int) -> int:
    initialize()
    with database.connection() as db:
        row = db.execute(
            "SELECT state_value FROM telegram_event_state WHERE state_key=?",
            (state_key,),
        ).fetchone()
    try:
        return int(row["state_value"]) if row is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _baseline_ms() -> int:
    return _state_ms(_BASELINE_KEY, _now_ms())


def _prediction_start_ms() -> int:
    baseline = _baseline_ms()
    return max(baseline, _state_ms(_PREDICTION_START_KEY, baseline))


def _lottery_name(key: str) -> str:
    spec = LOTTERIES.get(key)
    return spec.name if spec is not None else key


def _source_name(source: str) -> str:
    return {
        "ai": "天机云端 AI",
        "native": "天机云端本地",
    }.get(source, source)


def _numbers(raw: Any) -> list[int]:
    try:
        return [int(value) for value in json.loads(str(raw))]
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _number_text(values: list[int]) -> str:
    return "、".join(f"{value:02d}" for value in values)


def format_prediction_message(
    forecast: Any,
    miss_streak: int | None = None,
) -> str:
    lottery = str(forecast["lottery"])
    source = str(forecast["source"])
    top6 = _numbers(forecast["top6_json"])
    top7 = _numbers(forecast["top7_json"])
    streak = max(0, int(miss_streak or 0))
    lines = [
        "🔮 <b>新一期云端 AI 预测</b>",
        "",
        f"<b>彩种：</b>{html.escape(_lottery_name(lottery))}",
        f"<b>目标期：</b><code>{html.escape(str(forecast['target_period']))}</code>",
        f"<b>来源：</b>{html.escape(_source_name(source))}",
        f"<b>模型：</b><code>{html.escape(str(forecast['model']))}</code>",
    ]
    if streak >= _STRONG_ALERT_AFTER_MISSES:
        lines.append(f"<b>🚨 加强关注：</b>Top 6 已连续 {streak} 期未中")
    elif streak > 0:
        lines.append(f"<b>当前状态：</b>Top 6 已连续 {streak} 期未中")
    else:
        lines.append("<b>当前状态：</b>连续未中计数为 0")
    lines.extend(
        [
            f"<b>预测名次：</b>第 {int(forecast['position_index']) + 1} 名",
            f"<b>Top 6：</b>{_number_text(top6)}",
        ]
    )
    if top7:
        lines.append(f"<b>Top 7：</b>{_number_text(top7)}")
    lines.append(
        f"<b>训练截止期：</b><code>{html.escape(str(forecast['trained_through_period']))}</code>"
    )
    lines.append("")
    if streak >= _STRONG_ALERT_AFTER_MISSES:
        lines.append("当前处于连续不中加强关注阶段；预测仍会逐期推送，恢复命中后发送一次结果提醒。")
    else:
        lines.append("云端 AI 预测将每期推送；连续三期 Top 6 未中时会发送加强提醒。")
    return "\n".join(lines)


def format_win_message(forecast: Any) -> str:
    lottery = str(forecast["lottery"])
    source = str(forecast["source"])
    top6 = _numbers(forecast["top6_json"])
    actual = int(forecast["actual_number"])
    try:
        hit_rank = top6.index(actual) + 1
    except ValueError:
        hit_rank = 0
    lines = [
        "🎉 <b>连续不中后恢复命中</b>",
        "",
        f"<b>彩种：</b>{html.escape(_lottery_name(lottery))}",
        f"<b>开奖期号：</b><code>{html.escape(str(forecast['target_period']))}</code>",
        f"<b>来源：</b>{html.escape(_source_name(source))}",
        f"<b>模型：</b><code>{html.escape(str(forecast['model']))}</code>",
        f"<b>预测名次：</b>第 {int(forecast['position_index']) + 1} 名",
        f"<b>预测 Top 6：</b>{_number_text(top6)}",
        f"<b>实际号码：</b><b>{actual:02d}</b>",
    ]
    if hit_rank:
        lines.append(f"<b>命中顺位：</b>Top 6 第 {hit_rank} 位")
    lines.extend(
        [
            "",
            "连续不中计数已清零；下一期云端 AI 预测仍会正常推送。",
        ]
    )
    return "\n".join(lines)


def _consecutive_misses_before(db: Any, forecast: Any) -> int:
    rows = db.execute(
        """
        SELECT top6_hit
        FROM forecasts
        WHERE lottery=?
          AND source=?
          AND model=?
          AND id<?
          AND settled_at IS NOT NULL
        ORDER BY id DESC
        LIMIT 1000
        """,
        (
            str(forecast["lottery"]),
            str(forecast["source"]),
            str(forecast["model"]),
            int(forecast["id"]),
        ),
    ).fetchall()
    streak = 0
    for row in rows:
        if int(row["top6_hit"]) == 1:
            break
        streak += 1
    return streak


def _event_forecast(event_key: str, prefix: str) -> Any | None:
    if not event_key.startswith(prefix + ":"):
        return None
    try:
        forecast_id = int(event_key.split(":", 1)[1])
    except (IndexError, ValueError):
        return None
    with database.connection() as db:
        return db.execute(
            "SELECT * FROM forecasts WHERE id=?",
            (forecast_id,),
        ).fetchone()


def _prediction_event_is_eligible(event_key: str) -> bool:
    forecast = _event_forecast(event_key, "prediction")
    return bool(
        forecast is not None
        and str(forecast["source"]) == "ai"
        and forecast["settled_at"] is None
    )


def _win_event_is_eligible(event_key: str) -> bool:
    forecast = _event_forecast(event_key, "win")
    if (
        forecast is None
        or str(forecast["source"]) != "ai"
        or forecast["settled_at"] is None
        or int(forecast["top6_hit"] or 0) != 1
    ):
        return False
    with database.connection() as db:
        return (
            _consecutive_misses_before(db, forecast)
            >= _STRONG_ALERT_AFTER_MISSES
        )


def materialize_events(lottery_filter: str | None = None) -> int:
    initialize()
    baseline = _baseline_ms()
    prediction_start = _prediction_start_ms()
    lottery_sql = " AND lottery=?" if lottery_filter else ""
    prediction_params: tuple[Any, ...] = (
        (prediction_start, lottery_filter)
        if lottery_filter
        else (prediction_start,)
    )
    win_params: tuple[Any, ...] = (
        (baseline, lottery_filter) if lottery_filter else (baseline,)
    )
    with database.connection() as db:
        predictions = db.execute(
            f"""
            SELECT * FROM forecasts
            WHERE created_at>=?
              AND source='ai'
              AND settled_at IS NULL{lottery_sql}
            ORDER BY id DESC
            LIMIT 1000
            """,
            prediction_params,
        ).fetchall()
        wins = db.execute(
            f"""
            SELECT * FROM forecasts
            WHERE settled_at IS NOT NULL
              AND settled_at>=?
              AND source='ai'
              AND top6_hit=1{lottery_sql}
            ORDER BY id DESC
            LIMIT 1000
            """,
            win_params,
        ).fetchall()

        created = 0
        now = _now_ms()
        for row in predictions:
            miss_streak = _consecutive_misses_before(db, row)
            cursor = db.execute(
                """
                INSERT OR IGNORE INTO telegram_events(
                    event_key,event_type,lottery,source,model,target_period,
                    message_html,created_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    f"prediction:{int(row['id'])}",
                    "prediction",
                    str(row["lottery"]),
                    str(row["source"]),
                    str(row["model"]),
                    str(row["target_period"]),
                    format_prediction_message(row, miss_streak),
                    int(row["created_at"] or now),
                ),
            )
            created += int(bool(cursor.rowcount))

        for row in wins:
            if (
                _consecutive_misses_before(db, row)
                < _STRONG_ALERT_AFTER_MISSES
            ):
                continue
            cursor = db.execute(
                """
                INSERT OR IGNORE INTO telegram_events(
                    event_key,event_type,lottery,source,model,target_period,
                    message_html,created_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    f"win:{int(row['id'])}",
                    "win",
                    str(row["lottery"]),
                    str(row["source"]),
                    str(row["model"]),
                    str(row["target_period"]),
                    format_win_message(row),
                    int(row["settled_at"] or now),
                ),
            )
            created += int(bool(cursor.rowcount))
    return created


def _claim_delivery(event_key: str, target_key: str, now: int) -> bool:
    retry_before = now - _RETRY_COOLDOWN_MS
    with database.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            """
            SELECT status,attempted_at
            FROM telegram_event_deliveries
            WHERE event_key=? AND target_key=?
            """,
            (event_key, target_key),
        ).fetchone()
        if row is not None:
            if str(row["status"]) in {"sent", "suppressed"}:
                return False
            if int(row["attempted_at"]) > retry_before:
                return False
        db.execute(
            """
            INSERT INTO telegram_event_deliveries(
                event_key,target_key,status,response_code,message,attempted_at
            ) VALUES(?,?,'sending',NULL,'',?)
            ON CONFLICT(event_key,target_key) DO UPDATE SET
                status='sending',response_code=NULL,message='',attempted_at=excluded.attempted_at
            """,
            (event_key, target_key, now),
        )
    return True


def _suppress_delivery(
    event_key: str,
    target_key: str,
    *,
    attempted_at: int,
    message: str,
) -> None:
    with database.connection() as db:
        db.execute(
            """
            INSERT INTO telegram_event_deliveries(
                event_key,target_key,status,response_code,message,attempted_at
            ) VALUES(?,?,'suppressed',NULL,?,?)
            ON CONFLICT(event_key,target_key) DO UPDATE SET
                status='suppressed',response_code=NULL,
                message=excluded.message,attempted_at=excluded.attempted_at
            """,
            (event_key, target_key, message[:800], attempted_at),
        )


def _finish_delivery(
    event_key: str,
    target_key: str,
    *,
    ok: bool,
    code: int | None,
    message: str,
    attempted_at: int,
) -> None:
    with database.connection() as db:
        db.execute(
            """
            UPDATE telegram_event_deliveries
            SET status=?,response_code=?,message=?,attempted_at=?
            WHERE event_key=? AND target_key=?
            """,
            (
                "sent" if ok else "failed",
                code,
                message[:800],
                attempted_at,
                event_key,
                target_key,
            ),
        )


def deliver_pending_events() -> dict[str, int]:
    initialize()
    if not settings.telegram_enabled:
        return {"sent": 0, "failed": 0, "skipped": 0}

    sent = failed = skipped = 0
    for chat_id in settings.telegram_chat_ids:
        target_key = telegram_alerts.delivery_key(chat_id)
        with database.connection() as db:
            events = db.execute(
                """
                SELECT event.*
                FROM telegram_events AS event
                LEFT JOIN telegram_event_deliveries AS delivery
                  ON delivery.event_key=event.event_key
                 AND delivery.target_key=?
                WHERE event.source='ai'
                  AND (
                    delivery.status IS NULL
                    OR delivery.status NOT IN ('sent','suppressed')
                  )
                ORDER BY CASE event.event_type WHEN 'win' THEN 0 ELSE 1 END,
                         event.created_at DESC
                LIMIT ?
                """,
                (target_key, _MAX_PENDING_PER_TARGET),
            ).fetchall()

        for event in events:
            event_key = str(event["event_key"])
            event_type = str(event["event_type"])
            now = _now_ms()
            if (
                event_type == "prediction"
                and now - int(event["created_at"] or now) > _MAX_PREDICTION_EVENT_AGE_MS
            ):
                _suppress_delivery(
                    event_key,
                    target_key,
                    attempted_at=now,
                    message="预测消息已超过8分钟，避免迟到推送",
                )
                skipped += 1
                continue
            if (
                event_type == "prediction"
                and not _prediction_event_is_eligible(event_key)
            ):
                _suppress_delivery(
                    event_key,
                    target_key,
                    attempted_at=now,
                    message="预测目标期已经开奖，或事件不是云端 AI 来源",
                )
                skipped += 1
                continue
            if event_type == "win" and not _win_event_is_eligible(event_key):
                _suppress_delivery(
                    event_key,
                    target_key,
                    attempted_at=now,
                    message="普通中奖不推送，仅连续三期不中后的恢复命中才提醒",
                )
                skipped += 1
                continue
            if not _claim_delivery(event_key, target_key, now):
                skipped += 1
                continue
            ok, code, message = telegram_alerts.send_html_message(
                bot_token=settings.telegram_bot_token,
                chat_id=chat_id,
                text=str(event["message_html"]),
            )
            _finish_delivery(
                event_key,
                target_key,
                ok=ok,
                code=code,
                message=message,
                attempted_at=now,
            )
            if ok:
                sent += 1
            else:
                failed += 1
    return {"sent": sent, "failed": failed, "skipped": skipped}


def process(lottery_filter: str | None = None) -> dict[str, Any]:
    initialize()
    created = materialize_events(lottery_filter)
    delivery = deliver_pending_events()
    return {
        "created": created,
        "delivery": delivery,
        "configured": settings.telegram_enabled,
    }
