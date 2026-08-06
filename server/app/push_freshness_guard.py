from __future__ import annotations

import time
from typing import Any

from . import push_alerts, push_runtime_v2
from .db import database
from .lottery import parse_epoch_ms


_WARNING_EVENT_TYPES = {"miss_prealert", "miss_alert", "miss_escalation"}
_SETTLEMENT_FRESH_MS = 20 * 60 * 1000
_ALERT_FRESH_MS = 30 * 60 * 1000
_DRAW_FRESH_MS = 60 * 60 * 1000
_INSTALLED = False
_ORIGINAL_MATERIALIZE = None
_ORIGINAL_DELIVERY_CANDIDATES = None


def _now_ms() -> int:
    return int(time.time() * 1000)


def _warning_candidate_is_fresh(
    *,
    target_period: str,
    latest_period: str,
    settled_at: int | None,
    draw_time: str,
    created_at: int | None,
    now_ms: int,
) -> bool:
    """Fail closed unless the alert belongs to a draw that just settled."""
    if not target_period or target_period != latest_period:
        return False
    if settled_at is None or created_at is None:
        return False
    if settled_at > now_ms or now_ms - settled_at > _SETTLEMENT_FRESH_MS:
        return False
    if created_at > now_ms or now_ms - created_at > _ALERT_FRESH_MS:
        return False
    draw_at = parse_epoch_ms(draw_time)
    if draw_at is None:
        return False
    draw_age = now_ms - draw_at
    return 0 <= draw_age <= _DRAW_FRESH_MS


def _prediction_target_period(prediction: dict[str, Any]) -> str:
    recent = list(prediction.get("recent_three") or [])
    if recent:
        value = str(recent[0].get("target_period") or "")
        if value:
            return value
    return str(prediction.get("latest_target_period") or "")


def _fresh_prediction_warning(
    *,
    lottery: str,
    prediction: dict[str, Any],
    latest_period: str,
    now_ms: int,
) -> bool:
    target_period = _prediction_target_period(prediction)
    source = str(prediction.get("source") or "")
    model = str(prediction.get("model") or "")
    if not target_period or not source or not model or not latest_period:
        return False
    with database.connection() as db:
        row = db.execute(
            """
            SELECT f.settled_at,d.draw_time
            FROM forecasts AS f
            LEFT JOIN draws AS d
              ON d.lottery=f.lottery AND d.period=f.target_period
            WHERE f.lottery=? AND f.source=? AND f.model=? AND f.target_period=?
            ORDER BY f.id DESC
            LIMIT 1
            """,
            (lottery, source, model, target_period),
        ).fetchone()
    if row is None:
        return False
    return _warning_candidate_is_fresh(
        target_period=target_period,
        latest_period=latest_period,
        settled_at=(None if row["settled_at"] is None else int(row["settled_at"])),
        draw_time=str(row["draw_time"] or ""),
        created_at=now_ms,
        now_ms=now_ms,
    )


def _filter_watch_for_fresh_settlements(
    watch: dict[str, Any],
    *,
    now_ms: int | None = None,
) -> dict[str, Any]:
    now = _now_ms() if now_ms is None else int(now_ms)
    lotteries_out: list[dict[str, Any]] = []
    warning_count = 0

    with database.connection() as db:
        latest_periods = {
            str(row["lottery"]): str(row["period"])
            for row in db.execute(
                """
                SELECT d.lottery,d.period
                FROM draws AS d
                INNER JOIN (
                    SELECT lottery,MAX(LENGTH(period)) AS max_length
                    FROM draws
                    GROUP BY lottery
                ) AS lengths
                  ON lengths.lottery=d.lottery
                 AND lengths.max_length=LENGTH(d.period)
                WHERE d.period=(
                    SELECT MAX(d2.period)
                    FROM draws AS d2
                    WHERE d2.lottery=d.lottery
                      AND LENGTH(d2.period)=lengths.max_length
                )
                """
            ).fetchall()
        }

    for lottery_value in list(watch.get("lotteries") or []):
        lottery = dict(lottery_value)
        lottery_key = str(lottery.get("key") or "")
        latest_period = latest_periods.get(lottery_key, "")
        predictions_out: list[dict[str, Any]] = []
        for prediction_value in list(lottery.get("predictions") or []):
            prediction = dict(prediction_value)
            if bool(prediction.get("warning")):
                fresh = _fresh_prediction_warning(
                    lottery=lottery_key,
                    prediction=prediction,
                    latest_period=latest_period,
                    now_ms=now,
                )
                prediction["warning"] = fresh
                if fresh:
                    warning_count += 1
            predictions_out.append(prediction)
        lottery["predictions"] = predictions_out
        lottery["warning_count"] = sum(
            1 for item in predictions_out if bool(item.get("warning"))
        )
        lotteries_out.append(lottery)

    result = dict(watch)
    result["warning_count"] = warning_count
    result["lotteries"] = lotteries_out
    result["generated_at_epoch_ms"] = now
    return result


def _materialize_fresh_warning_alerts(
    watch: dict[str, Any],
    *,
    lottery_filter: str | None = None,
) -> list[int]:
    if _ORIGINAL_MATERIALIZE is None:
        return []
    filtered = _filter_watch_for_fresh_settlements(watch)
    return _ORIGINAL_MATERIALIZE(filtered, lottery_filter=lottery_filter)


def _latest_period_map() -> dict[str, str]:
    with database.connection() as db:
        rows = db.execute(
            """
            SELECT d.lottery,d.period
            FROM draws AS d
            INNER JOIN (
                SELECT lottery,MAX(LENGTH(period)) AS max_length
                FROM draws
                GROUP BY lottery
            ) AS lengths
              ON lengths.lottery=d.lottery
             AND lengths.max_length=LENGTH(d.period)
            WHERE d.period=(
                SELECT MAX(d2.period)
                FROM draws AS d2
                WHERE d2.lottery=d.lottery
                  AND LENGTH(d2.period)=lengths.max_length
            )
            """
        ).fetchall()
    return {str(row["lottery"]): str(row["period"]) for row in rows}


def _expire_invalid_warning_alerts(now_ms: int | None = None) -> set[int]:
    now = _now_ms() if now_ms is None else int(now_ms)
    latest_periods = _latest_period_map()
    placeholders = ",".join("?" for _ in _WARNING_EVENT_TYPES)
    with database.connection() as db:
        rows = db.execute(
            f"""
            SELECT
                a.id,a.collapse_key,a.lottery,a.latest_target_period,a.created_at,
                f.settled_at,d.draw_time
            FROM push_alerts AS a
            LEFT JOIN forecasts AS f
              ON f.lottery=a.lottery
             AND f.source=a.source
             AND f.model=a.model
             AND f.target_period=a.latest_target_period
            LEFT JOIN draws AS d
              ON d.lottery=a.lottery
             AND d.period=a.latest_target_period
            WHERE a.event_type IN ({placeholders})
              AND (a.expires_at IS NULL OR a.expires_at>?)
            ORDER BY a.id DESC
            """,
            (*sorted(_WARNING_EVENT_TYPES), now),
        ).fetchall()

        valid_ids: set[int] = set()
        invalid_ids: list[int] = []
        seen_collapse_keys: set[str] = set()
        for row in rows:
            alert_id = int(row["id"])
            collapse_key = str(row["collapse_key"] or row["lottery"])
            if collapse_key in seen_collapse_keys:
                invalid_ids.append(alert_id)
                continue
            seen_collapse_keys.add(collapse_key)
            fresh = _warning_candidate_is_fresh(
                target_period=str(row["latest_target_period"] or ""),
                latest_period=latest_periods.get(str(row["lottery"]), ""),
                settled_at=(
                    None if row["settled_at"] is None else int(row["settled_at"])
                ),
                draw_time=str(row["draw_time"] or ""),
                created_at=int(row["created_at"]),
                now_ms=now,
            )
            if fresh:
                valid_ids.add(alert_id)
            else:
                invalid_ids.append(alert_id)

        if invalid_ids:
            expire_placeholders = ",".join("?" for _ in invalid_ids)
            db.execute(
                f"UPDATE push_alerts SET expires_at=? WHERE id IN ({expire_placeholders})",
                (now, *invalid_ids),
            )
    return valid_ids


def _warning_row(row: Any) -> bool:
    return str(row["event_type"] or "") in _WARNING_EVENT_TYPES


def _delivery_candidates_with_freshness() -> tuple[list[Any], list[Any]]:
    if _ORIGINAL_DELIVERY_CANDIDATES is None:
        return [], []
    valid_warning_ids = _expire_invalid_warning_alerts()
    fcm_rows, alerts = _ORIGINAL_DELIVERY_CANDIDATES()
    filtered_fcm = [
        row
        for row in fcm_rows
        if not _warning_row(row) or int(row["id"]) in valid_warning_ids
    ]
    filtered_alerts = [
        row
        for row in alerts
        if not _warning_row(row) or int(row["id"]) in valid_warning_ids
    ]
    return filtered_fcm, filtered_alerts


def install() -> None:
    global _INSTALLED, _ORIGINAL_MATERIALIZE, _ORIGINAL_DELIVERY_CANDIDATES
    if _INSTALLED:
        return
    _ORIGINAL_MATERIALIZE = push_alerts.materialize_warning_alerts
    _ORIGINAL_DELIVERY_CANDIDATES = push_runtime_v2._delivery_candidates
    push_alerts.materialize_warning_alerts = _materialize_fresh_warning_alerts
    push_runtime_v2._delivery_candidates = _delivery_candidates_with_freshness
    _expire_invalid_warning_alerts()
    _INSTALLED = True
