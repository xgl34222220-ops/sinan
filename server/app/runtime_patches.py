from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from . import admin_insights


_INSTALLED = False
_PERIOD_RE = re.compile(r"^(.*?)(\d+)$")


def _record_group_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("lottery") or ""),
        str(record.get("source") or ""),
        str(record.get("model") or ""),
    )


def _period_sort_key(record: dict[str, Any]) -> tuple[str, int, int, int]:
    period = str(record.get("target_period") or "")
    match = _PERIOD_RE.match(period)
    prefix = match.group(1) if match else period
    number = int(match.group(2)) if match else -1
    created = int(record.get("created_at_epoch_ms") or 0)
    record_id = int(record.get("id") or 0)
    return prefix, number, created, record_id


def _canonical_grouped_rows(
    rows_desc: list[dict[str, Any]],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    seen: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for record in rows_desc:
        if record.get("top6_hit") is None:
            continue
        key = _record_group_key(record)
        target_period = str(record.get("target_period") or "")
        if not all(key) or not target_period or target_period in seen[key]:
            continue
        seen[key].add(target_period)
        grouped[key].append(record)
    for values in grouped.values():
        values.sort(key=_period_sort_key, reverse=True)
    return grouped


def _single_streak(rows_desc: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows_desc:
        return {"current_type": None, "current": 0, "longest_miss": 0}

    current_type = "hit" if rows_desc[0].get("top6_hit") is True else "miss"
    current = 0
    for record in rows_desc:
        record_type = "hit" if record.get("top6_hit") is True else "miss"
        if record_type != current_type:
            break
        current += 1

    longest_miss = 0
    running_miss = 0
    for record in reversed(rows_desc):
        if record.get("top6_hit") is True:
            running_miss = 0
        else:
            running_miss += 1
            longest_miss = max(longest_miss, running_miss)

    return {
        "current_type": current_type,
        "current": current,
        "longest_miss": longest_miss,
    }


def _leader_payload(
    key: tuple[str, str, str] | None,
    streak: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if key is None or streak is None:
        return None
    lottery, source, model = key
    return {
        "lottery": lottery,
        "lottery_name": (
            admin_insights.LOTTERIES[lottery].name
            if lottery in admin_insights.LOTTERIES
            else lottery
        ),
        "source": source,
        "source_name": "天机云端 AI" if source == "ai" else "天机云端本地",
        "model": model,
        **streak,
    }


def _scope_streak(rows_desc: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = _canonical_grouped_rows(rows_desc)
    if not grouped:
        return {
            "current_type": None,
            "current": 0,
            "longest_miss": 0,
            "group_count": 0,
            "current_leader": None,
            "longest_miss_leader": None,
        }

    streaks = {key: _single_streak(values) for key, values in grouped.items()}
    miss_current = [
        (key, value)
        for key, value in streaks.items()
        if value["current_type"] == "miss"
    ]
    if miss_current:
        current_key, current_streak = max(
            miss_current,
            key=lambda item: (
                int(item[1]["current"]),
                int(item[1]["longest_miss"]),
                item[0],
            ),
        )
    else:
        current_key, current_streak = max(
            streaks.items(),
            key=lambda item: (
                int(item[1]["current"]),
                int(item[1]["longest_miss"]),
                item[0],
            ),
        )

    longest_key, longest_streak = max(
        streaks.items(),
        key=lambda item: (
            int(item[1]["longest_miss"]),
            int(item[1]["current"]),
            item[0],
        ),
    )
    return {
        "current_type": current_streak["current_type"],
        "current": int(current_streak["current"]),
        "longest_miss": int(longest_streak["longest_miss"]),
        "group_count": len(grouped),
        "current_leader": _leader_payload(current_key, current_streak),
        "longest_miss_leader": _leader_payload(longest_key, longest_streak),
    }


def _group_summary_fixed(rows_desc: list[dict[str, Any]]) -> dict[str, Any]:
    settled = [row for row in rows_desc if row.get("top6_hit") is not None]
    windows: dict[str, Any] = {}
    for size in (20, 50, 100):
        scoped = settled[:size]
        value = admin_insights._rate(scoped)
        value["streak"] = _scope_streak(scoped)
        windows[str(size)] = value

    all_value = admin_insights._rate(rows_desc)
    all_value["streak"] = _scope_streak(rows_desc)
    windows["all"] = all_value

    position_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    latencies: list[float] = []
    for row in rows_desc:
        position_rows[int(row.get("position") or 0)].append(row)
        match = admin_insights._LATENCY_RE.search(str(row.get("analysis") or ""))
        if match:
            latencies.append(float(match.group(1)))

    positions = []
    for position in range(10):
        value = admin_insights._rate(position_rows.get(position, []))
        value["position"] = position
        value["streak"] = _scope_streak(position_rows.get(position, []))
        positions.append(value)

    return {
        **admin_insights._rate(rows_desc),
        "windows": windows,
        "streak": _scope_streak(rows_desc),
        "positions": positions,
        "average_latency_seconds": (
            round(sum(latencies) / len(latencies), 2) if latencies else None
        ),
    }


def install() -> None:
    """Install reporting fixes only.

    Runtime patches used to force cloud AI away from the native Top6 whenever
    the two sources overlapped. That policy is intentionally removed: agreement
    between independently generated forecasts is not an error condition and
    must never mutate or reject an AI forecast.
    """
    global _INSTALLED
    if _INSTALLED:
        return
    admin_insights._group_summary = _group_summary_fixed
    _INSTALLED = True
