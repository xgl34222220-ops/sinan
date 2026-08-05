from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import glob
import json
import os
import re
import shutil
from typing import Any

from .config import settings
from .db import database
from .models import LOTTERIES


_LATENCY_RE = re.compile(r"云端耗时\s+([0-9]+(?:\.[0-9]+)?)s")
_PERIOD_RE = re.compile(r"^(.*?)(\d+)$")


def _record_dict(row: Any) -> dict[str, Any]:
    source = str(row["source"])
    lottery = str(row["lottery"])
    return {
        "id": int(row["id"]),
        "lottery": lottery,
        "lottery_name": LOTTERIES.get(lottery).name if lottery in LOTTERIES else lottery,
        "target_period": str(row["target_period"]),
        "trained_through_period": str(row["trained_through_period"]),
        "position": int(row["position_index"]),
        "top6": json.loads(row["top6_json"]),
        "top7": json.loads(row["top7_json"]),
        "probabilities": json.loads(row["probabilities_json"]),
        "source": source,
        "source_name": "天机云端 AI" if source == "ai" else "天机云端本地",
        "model": str(row["model"]),
        "analysis": str(row["analysis"] or ""),
        "risk_note": str(row["risk_note"] or ""),
        "created_at_epoch_ms": int(row["created_at"]),
        "actual_number": row["actual_number"],
        "top6_hit": None if row["top6_hit"] is None else bool(row["top6_hit"]),
        "top7_hit": None if row["top7_hit"] is None else bool(row["top7_hit"]),
        "settled_at_epoch_ms": row["settled_at"],
    }


def _filters(
    *,
    lottery: str = "all",
    source: str = "all",
    status: str = "all",
    model: str = "",
    days: int = 0,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if lottery != "all":
        if lottery not in LOTTERIES:
            raise ValueError("未知彩种")
        clauses.append("lottery = ?")
        params.append(lottery)
    if source != "all":
        if source not in {"ai", "native"}:
            raise ValueError("未知预测来源")
        clauses.append("source = ?")
        params.append(source)
    if status == "pending":
        clauses.append("settled_at IS NULL")
    elif status == "hit":
        clauses.append("top6_hit = 1")
    elif status == "miss":
        clauses.append("top6_hit = 0")
    elif status != "all":
        raise ValueError("未知结算状态")
    if model.strip():
        clauses.append("model = ?")
        params.append(model.strip())
    if days > 0:
        clauses.append("created_at >= ?")
        params.append(
            int(datetime.now(tz=timezone.utc).timestamp() * 1000)
            - int(days) * 86_400_000
        )
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def records_page(
    *,
    lottery: str = "all",
    source: str = "all",
    status: str = "all",
    model: str = "",
    days: int = 0,
    limit: int = 24,
    offset: int = 0,
) -> dict[str, Any]:
    safe_limit = max(1, min(100, int(limit)))
    safe_offset = max(0, int(offset))
    where, params = _filters(
        lottery=lottery,
        source=source,
        status=status,
        model=model,
        days=days,
    )
    model_where, model_params = _filters(
        lottery=lottery,
        source=source,
        status="all",
        model="",
        days=days,
    )
    with database.connection() as db:
        total = int(
            db.execute(f"SELECT COUNT(*) FROM forecasts{where}", params).fetchone()[0]
        )
        rows = db.execute(
            f"SELECT * FROM forecasts{where} "
            "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            [*params, safe_limit, safe_offset],
        ).fetchall()
        model_rows = db.execute(
            f"SELECT model, source, COUNT(*) AS count FROM forecasts{model_where} "
            "GROUP BY model, source ORDER BY count DESC, model ASC",
            model_params,
        ).fetchall()
    return {
        "items": [_record_dict(row) for row in rows],
        "total": total,
        "limit": safe_limit,
        "offset": safe_offset,
        "has_more": safe_offset + len(rows) < total,
        "models": [
            {
                "model": str(row["model"]),
                "source": str(row["source"]),
                "count": int(row["count"]),
            }
            for row in model_rows
        ],
    }


def _rate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    settled = [row for row in rows if row["top6_hit"] is not None]
    hits = sum(1 for row in settled if row["top6_hit"] is True)
    return {
        "count": len(rows),
        "settled": len(settled),
        "pending": len(rows) - len(settled),
        "hits": hits,
        "misses": len(settled) - hits,
        "hit_rate": round(hits / len(settled), 4) if settled else None,
    }


def _streak(rows_desc: list[dict[str, Any]]) -> dict[str, Any]:
    settled_desc = [row for row in rows_desc if row["top6_hit"] is not None]
    if not settled_desc:
        return {"current_type": None, "current": 0, "longest_miss": 0}
    current_type = "hit" if settled_desc[0]["top6_hit"] else "miss"
    current = 0
    for row in settled_desc:
        row_type = "hit" if row["top6_hit"] else "miss"
        if row_type != current_type:
            break
        current += 1
    longest_miss = 0
    running_miss = 0
    for row in reversed(settled_desc):
        if row["top6_hit"]:
            running_miss = 0
        else:
            running_miss += 1
            longest_miss = max(longest_miss, running_miss)
    return {
        "current_type": current_type,
        "current": current,
        "longest_miss": longest_miss,
    }


def _group_summary(rows_desc: list[dict[str, Any]]) -> dict[str, Any]:
    settled = [row for row in rows_desc if row["top6_hit"] is not None]
    windows: dict[str, Any] = {}
    for size in (20, 50, 100):
        windows[str(size)] = _rate(settled[:size])
    windows["all"] = _rate(rows_desc)

    position_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    latencies: list[float] = []
    for row in rows_desc:
        position_rows[int(row["position"])].append(row)
        match = _LATENCY_RE.search(row["analysis"])
        if match:
            latencies.append(float(match.group(1)))
    positions = []
    for position in range(10):
        value = _rate(position_rows.get(position, []))
        value["position"] = position
        positions.append(value)
    return {
        **_rate(rows_desc),
        "windows": windows,
        "streak": _streak(rows_desc),
        "positions": positions,
        "average_latency_seconds": (
            round(sum(latencies) / len(latencies), 2) if latencies else None
        ),
    }


def records_insights(
    *,
    lottery: str = "all",
    source: str = "all",
    model: str = "",
    days: int = 0,
) -> dict[str, Any]:
    where, params = _filters(
        lottery=lottery,
        source=source,
        status="all",
        model=model,
        days=days,
    )
    with database.connection() as db:
        rows = db.execute(
            f"SELECT * FROM forecasts{where} ORDER BY created_at DESC, id DESC",
            params,
        ).fetchall()
        jobs = db.execute(
            "SELECT source, model, status, COUNT(*) AS count FROM forecast_jobs "
            "GROUP BY source, model, status"
        ).fetchall()
    values = [_record_dict(row) for row in rows]
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_model: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for value in values:
        by_source[value["source"]].append(value)
        by_model[(value["source"], value["model"])].append(value)

    job_counts: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for row in jobs:
        job_counts[(str(row["source"]), str(row["model"]))][
            str(row["status"])
        ] += int(row["count"])

    models = []
    for (model_source, model_name), group in sorted(
        by_model.items(), key=lambda item: len(item[1]), reverse=True
    ):
        summary = _group_summary(group)
        counts = dict(job_counts.get((model_source, model_name), {}))
        terminal = sum(
            counts.get(key, 0) for key in ("completed", "error", "discarded")
        )
        summary.update(
            {
                "source": model_source,
                "model": model_name,
                "job_counts": counts,
                "job_failure_rate": (
                    round(
                        (counts.get("error", 0) + counts.get("discarded", 0))
                        / terminal,
                        4,
                    )
                    if terminal
                    else None
                ),
            }
        )
        models.append(summary)

    return {
        "scope": {
            "lottery": lottery,
            "source": source,
            "model": model,
            "days": days,
        },
        "overall": _group_summary(values),
        "sources": {
            key: _group_summary(by_source.get(key, [])) for key in ("ai", "native")
        },
        "models": models,
        "generated_at_epoch_ms": int(
            datetime.now(tz=timezone.utc).timestamp() * 1000
        ),
    }



def _prediction_miss_watch_from_records(
    records_desc: list[dict[str, Any]],
    threshold: int = 3,
) -> dict[str, Any]:
    safe_threshold = max(1, int(threshold))
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    seen_periods: dict[tuple[str, str, str], set[str]] = defaultdict(set)

    for record in records_desc:
        lottery = str(record.get("lottery") or "")
        source = str(record.get("source") or "")
        model = str(record.get("model") or "")
        target_period = str(record.get("target_period") or "")
        if not lottery or not source or not model or not target_period:
            continue
        key = (lottery, source, model)
        if target_period in seen_periods[key]:
            continue
        seen_periods[key].add(target_period)
        grouped[key].append(record)

    predictions_by_lottery: dict[str, list[dict[str, Any]]] = defaultdict(list)
    warning_count = 0
    for (lottery, source, model), records in grouped.items():
        settled = [record for record in records if record.get("top6_hit") is not None]
        current_miss_streak = 0
        for record in settled:
            if record.get("top6_hit") is False:
                current_miss_streak += 1
            else:
                break
        warning = current_miss_streak >= safe_threshold
        if warning:
            warning_count += 1
        recent = settled[:safe_threshold]
        source_name = "天机云端 AI" if source == "ai" else "天机云端本地"
        predictions_by_lottery[lottery].append(
            {
                "source": source,
                "source_name": source_name,
                "model": model,
                "warning": warning,
                "threshold": safe_threshold,
                "current_miss_streak": current_miss_streak,
                "total_records": len(records),
                "settled_records": len(settled),
                "pending_records": len(records) - len(settled),
                "recent_three": [
                    {
                        "target_period": str(record.get("target_period") or ""),
                        "hit": bool(record.get("top6_hit")),
                        "actual_number": record.get("actual_number"),
                        "position": int(record.get("position") or 0),
                        "top6": list(record.get("top6") or []),
                        "settled_at_epoch_ms": record.get("settled_at_epoch_ms"),
                    }
                    for record in recent
                ],
            }
        )

    lotteries = []
    for key, spec in LOTTERIES.items():
        predictions = predictions_by_lottery.get(key, [])
        predictions.sort(
            key=lambda item: (
                not item["warning"],
                -int(item["current_miss_streak"]),
                str(item["source_name"]),
                str(item["model"]),
            )
        )
        lotteries.append(
            {
                "key": key,
                "name": spec.name,
                "warning_count": sum(1 for item in predictions if item["warning"]),
                "predictions": predictions,
            }
        )

    return {
        "threshold": safe_threshold,
        "warning_count": warning_count,
        "lotteries": lotteries,
        "generated_at_epoch_ms": int(
            datetime.now(tz=timezone.utc).timestamp() * 1000
        ),
    }


def prediction_miss_watch(threshold: int = 3) -> dict[str, Any]:
    with database.connection() as db:
        rows = db.execute(
            "SELECT * FROM forecasts ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return _prediction_miss_watch_from_records(
        [_record_dict(row) for row in rows],
        threshold=threshold,
    )


def _read_json_file(path: str) -> dict[str, Any] | None:
    try:
        with open(path, "r", encoding="utf-8") as file:
            value = json.load(file)
        return value if isinstance(value, dict) else {"value": value}
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def _period_parts(period: str) -> tuple[str, int] | None:
    match = _PERIOD_RE.match(period)
    if not match:
        return None
    return match.group(1), int(match.group(2))


def _data_integrity() -> dict[str, Any]:
    invalid_draws = 0
    missing_estimate = 0
    missing_examples: list[str] = []
    draw_counts: dict[str, int] = {}
    with database.connection() as db:
        integrity = str(db.execute("PRAGMA integrity_check").fetchone()[0])
        settlement_backlog = int(
            db.execute(
                "SELECT COUNT(*) FROM forecasts f JOIN draws d "
                "ON d.lottery=f.lottery AND d.period=f.target_period "
                "WHERE f.settled_at IS NULL"
            ).fetchone()[0]
        )
        for key in LOTTERIES:
            rows = db.execute(
                "SELECT period, numbers_json FROM draws WHERE lottery=? "
                "ORDER BY LENGTH(period) DESC, period DESC LIMIT 600",
                (key,),
            ).fetchall()
            draw_counts[key] = int(
                db.execute(
                    "SELECT COUNT(*) FROM draws WHERE lottery=?", (key,)
                ).fetchone()[0]
            )
            chronological = list(reversed(rows))
            previous: tuple[str, int] | None = None
            for row in chronological:
                parse_failed = False
                try:
                    numbers = json.loads(row["numbers_json"])
                except json.JSONDecodeError:
                    parse_failed = True
                    numbers = []
                if parse_failed or (
                    not isinstance(numbers, list)
                    or len(numbers) != 10
                    or len(set(numbers)) != 10
                    or any(
                        not isinstance(number, int) or number not in range(1, 11)
                        for number in numbers
                    )
                ):
                    invalid_draws += 1
                current = _period_parts(str(row["period"]))
                if (
                    previous
                    and current
                    and previous[0] == current[0]
                    and current[1] > previous[1] + 1
                ):
                    gap = current[1] - previous[1] - 1
                    missing_estimate += gap
                    if len(missing_examples) < 5:
                        missing_examples.append(
                            f"{key}: {previous[0]}{previous[1]} → "
                            f"{current[0]}{current[1]}，缺约 {gap} 期"
                        )
                previous = current
    return {
        "sqlite": integrity,
        "invalid_draws": invalid_draws,
        "settlement_backlog": settlement_backlog,
        "recent_missing_periods_estimate": missing_estimate,
        "missing_examples": missing_examples,
        "draw_counts": draw_counts,
        "ok": (
            integrity.lower() == "ok"
            and invalid_draws == 0
            and settlement_backlog == 0
        ),
    }


def _timeline() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with database.connection() as db:
        job_rows = db.execute(
            "SELECT lottery, target_period, model, status, message, attempts, "
            "updated_at FROM forecast_jobs ORDER BY updated_at DESC LIMIT 16"
        ).fetchall()
        forecast_rows = db.execute(
            "SELECT lottery, target_period, source, model, created_at "
            "FROM forecasts ORDER BY created_at DESC LIMIT 12"
        ).fetchall()
    for row in job_rows:
        lottery = str(row["lottery"])
        name = LOTTERIES.get(lottery).name if lottery in LOTTERIES else lottery
        status = str(row["status"])
        labels = {
            "queued": "AI 已排队",
            "running": "AI 正在分析",
            "completed": "AI 任务完成",
            "error": "AI 调用失败",
            "discarded": "AI 封盘丢弃",
        }
        events.append(
            {
                "time": int(row["updated_at"]),
                "type": "job",
                "level": (
                    "bad"
                    if status in {"error", "discarded"}
                    else "good" if status == "completed" else "warn"
                ),
                "title": f"{name} · {labels.get(status, status)}",
                "detail": str(
                    row["message"]
                    or f"目标期 {row['target_period']} · {row['model']}"
                )[:220],
            }
        )
    for row in forecast_rows:
        lottery = str(row["lottery"])
        name = LOTTERIES.get(lottery).name if lottery in LOTTERIES else lottery
        source = "云端 AI" if str(row["source"]) == "ai" else "本机云端"
        events.append(
            {
                "time": int(row["created_at"]),
                "type": "forecast",
                "level": "good",
                "title": f"{name} · {source}预测已冻结",
                "detail": f"目标期 {row['target_period']} · {row['model']}",
            }
        )
    for key, spec in LOTTERIES.items():
        state = database.get_state(f"cycle:{key}")
        if not state:
            continue
        try:
            value = json.loads(state[0])
        except json.JSONDecodeError:
            value = {}
        events.append(
            {
                "time": int(value.get("completed_at_epoch_ms") or state[1]),
                "type": "sync",
                "level": "good" if not value.get("errors") else "warn",
                "title": f"{spec.name} · 开奖同步完成",
                "detail": (
                    f"最新期 {value.get('latest_period', '—')} · "
                    f"目标期 {value.get('next_period', '—')} · "
                    f"结算 {value.get('settled', 0)} 条"
                ),
            }
        )
    return sorted(events, key=lambda item: item["time"], reverse=True)[:24]


def operations_overview() -> dict[str, Any]:
    status_path = os.path.join(settings.data_dir, "auto-update-status.json")
    update_status = _read_json_file(status_path) or {
        "status": "unknown",
        "message": "尚未读取到自动更新状态",
        "updated_at_epoch_ms": None,
    }
    backup_files = sorted(
        glob.glob("/app/backups/tianji-*.db.gz"),
        key=lambda path: os.path.getmtime(path),
        reverse=True,
    )
    latest_backup = None
    if backup_files:
        path = backup_files[0]
        latest_backup = {
            "name": os.path.basename(path),
            "size_bytes": os.path.getsize(path),
            "updated_at_epoch_ms": int(os.path.getmtime(path) * 1000),
        }
    db_size = (
        os.path.getsize(settings.database_path)
        if os.path.exists(settings.database_path)
        else 0
    )
    disk = shutil.disk_usage(settings.data_dir)
    return {
        "auto_update": update_status,
        "backup": {
            "count": len(backup_files),
            "latest": latest_backup,
        },
        "storage": {
            "database_size_bytes": db_size,
            "disk_total_bytes": disk.total,
            "disk_used_bytes": disk.used,
            "disk_free_bytes": disk.free,
            "disk_used_ratio": round(disk.used / disk.total, 4) if disk.total else None,
        },
        "integrity": _data_integrity(),
        "miss_watch": prediction_miss_watch(threshold=3),
        "timeline": _timeline(),
        "generated_at_epoch_ms": int(
            datetime.now(tz=timezone.utc).timestamp() * 1000
        ),
    }
