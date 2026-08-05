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
_PREDICTION_POLICY_KEY = "telegram_prediction_policy_two_misses_v1"
_TRACK_AFTER_MISSES = 2


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
            policy = db.execute(
                "SELECT 1 FROM telegram_event_state WHERE state_key=?",
                (_PREDICTION_POLICY_KEY,),
            ).fetchone()
            if policy is None:
                # 清除旧版“每期都推”的尚未成功发送队列。符合新规则的预测会在
                # 本轮 materialize_events 中以相同事件键重新生成。
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
                    (_PREDICTION_POLICY_KEY, "two_misses_until_hit", now),
                )
        _INITIALIZED = True


def _baseline_ms() -> int:
    initialize()
    with database.connection() as db:
        row = db.execute(
            "SELECT state_value FROM telegram_event_state WHERE state_key=?",
            (_BASELINE_KEY,),
        ).fetchone()
    try:
        return int(row["state_value"]) if row is not None else _now_ms()
    except (TypeError, ValueError):
        return _now_ms()


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
    lines = [
        "🔮 <b>追踪中的新一期预测</b>",
        "",
        f"<b>彩种：</b>{html.escape(_lottery_name(lottery))}",
        f"<b>目标期：</b><code>{html.escape(str(forecast['target_period']))}</code>",
        f"<b>来源：</b>{html.escape(_source_name(source))}",
        f"<b>模型：</b><code>{html.escape(str(forecast['model']))}</code>",
    ]
    if miss_streak is not None:
        lines.append(
            f"<b>追踪状态：</b>Top 6 已连续 {max(0, int(miss_streak))} 期未中"
        )
    lines.extend(
        [
            f"<b>预测名次：</b>第 {int(forecast['position_index']) + 1} 名",
            f"<b>Top 6：</b>{_number_text(top6)}",
        ]
    )
    if top7:
        lines.append(f"<b>Top 7：</b>{_number_text(top7)}")
    lines.extend(
        [
            f"<b>训练截止期：</b><code>{html.escape(str(forecast['trained_through_period']))}</code>",
            "",
            "已进入追踪推送；后续每期继续发送，下一次 Top 6 命中后自动停止预测推送。",
        ]
    )
    return "\n".join(lines)


def format_win_message(
    forecast: Any,
    tracking_was_active: bool = False,
) -> str:
    lottery = str(forecast["lottery"])
    source = str(forecast["source"])
    top6 = _numbers(forecast["top6_json"])
    actual = int(forecast["actual_number"])
    try:
        hit_rank = top6.index(actual) + 1
    except ValueError:
        hit_rank = 0
    lines = [
        "🎉 <b>Top 6 命中</b>",
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
    lines.append("")
    if tracking_was_active:
        lines.append("该预测已完成真实前向开奖结算；本轮追踪预测推送现已停止。")
    else:
        lines.append("该预测已完成真实前向开奖结算。")
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


def _prediction_event_is_eligible(event_key: str) -> bool:
    if not event_key.startswith("prediction:"):
        return True
    try:
        forecast_id = int(event_key.split(":", 1)[1])
    except (IndexError, ValueError):
        return False
    with database.connection() as db:
        forecast = db.execute(
            "SELECT * FROM forecasts WHERE id=?",
            (forecast_id,),
        ).fetchone()
        if forecast is None or forecast["settled_at"] is not None:
            return False
        return _consecutive_misses_before(db, forecast) >= _TRACK_AFTER_MISSES


def materialize_events(lottery_filter: str | None = None) -> int:
    initialize()
    baseline = _baseline_ms()
    lottery_sql = " AND lottery=?" if lottery_filter else ""
    params: tuple[Any, ...] = (baseline, lottery_filter) if lottery_filter else (baseline,)
    with database.connection() as db:
        predictions = db.execute(
            f"""
            SELECT * FROM forecasts
            WHERE created_at>=?{lottery_sql}
            ORDER BY id DESC
            LIMIT 1000
            """,
            params,
        ).fetchall()
        wins = db.execute(
            f"""
            SELECT * FROM forecasts
            WHERE settled_at IS NOT NULL
              AND settled_at>=?
              AND top6_hit=1{lottery_sql}
            ORDER BY id DESC
            LIMIT 1000
            """,
            params,
        ).fetchall()

        created = 0
        now = _now_ms()
        for row in predictions:
            miss_streak = _consecutive_misses_before(db, row)
            if miss_streak < _TRACK_AFTER_MISSES:
                continue
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
            tracking_was_active = (
                _consecutive_misses_before(db, row) >= _TRACK_AFTER_MISSES
            )
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
                    format_win_message(row, tracking_was_active),
                    int(row["settled_at"] or now),
                ),
            )
            created += int(bool(cursor.rowcount))
    return created


def _claim_delivery(event_key: str, target_key: str, now: int) -> bool:
    retry_before = now - 300_000
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
                WHERE delivery.status IS NULL
                   OR delivery.status NOT IN ('sent','suppressed')
                ORDER BY event.created_at ASC
                LIMIT 500
                """,
                (target_key,),
            ).fetchall()

        for event in events:
            event_key = str(event["event_key"])
            now = _now_ms()
            if (
                str(event["event_type"]) == "prediction"
                and not _prediction_event_is_eligible(event_key)
            ):
                _suppress_delivery(
                    event_key,
                    target_key,
                    attempted_at=now,
                    message="预测未达到连续两期未中条件，或目标期已经开奖",
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
