from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import signal
import sqlite3
import threading
import time

from .config import settings
from .db import database


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("tianji.backup")
stop_event = threading.Event()
BACKUP_DIR = Path(os.getenv("TIANJI_BACKUP_DIR", "./backups")).resolve()


def _log(event: str, **payload) -> None:
    logger.info(
        json.dumps(
            {"event": event, "at_epoch_ms": int(time.time() * 1000), **payload},
            ensure_ascii=False,
            default=str,
        )
    )


def _stop(signum: int, _frame: object) -> None:
    _log("backup_stop_requested", signal=signum)
    stop_event.set()


def _integrity_ok(path: Path) -> bool:
    with sqlite3.connect(path) as connection:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    return bool(row and str(row[0]).lower() == "ok")


def _backup_once() -> dict[str, object]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    source_path = Path(settings.database_path)
    if not source_path.exists():
        raise FileNotFoundError(f"数据库不存在：{source_path}")

    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    target = BACKUP_DIR / f"tianji-{stamp}.db"
    temporary = target.with_suffix(".db.tmp")
    started = time.monotonic()

    with sqlite3.connect(source_path) as source, sqlite3.connect(temporary) as destination:
        source.backup(destination, pages=256, sleep=0.05)
        destination.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    if not _integrity_ok(temporary):
        temporary.unlink(missing_ok=True)
        raise RuntimeError("备份完整性检查失败")

    os.replace(temporary, target)
    duration_ms = round((time.monotonic() - started) * 1000, 1)
    result = {
        "status": "ok",
        "path": str(target),
        "bytes": target.stat().st_size,
        "duration_ms": duration_ms,
        "completed_at_epoch_ms": int(time.time() * 1000),
    }
    database.set_state("backup_status", json.dumps(result, ensure_ascii=False))
    _prune_backups()
    return result


def _prune_backups() -> None:
    files = sorted(BACKUP_DIR.glob("tianji-????????-??????.db"), reverse=True)
    daily_keep: set[Path] = set()
    seen_days: set[str] = set()
    for path in files:
        day = path.name[7:15]
        if day in seen_days:
            continue
        seen_days.add(day)
        daily_keep.add(path)
        if len(daily_keep) >= settings.backup_retention_daily:
            break

    monthly_keep: set[Path] = set()
    seen_months: set[str] = set()
    for path in files:
        month = path.name[7:13]
        if month in seen_months:
            continue
        seen_months.add(month)
        monthly_keep.add(path)
        if len(monthly_keep) >= settings.backup_retention_monthly:
            break

    keep = daily_keep | monthly_keep
    for path in files:
        if path not in keep:
            path.unlink(missing_ok=True)


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    _log(
        "backup_started",
        interval_seconds=settings.backup_interval_seconds,
        daily_retention=settings.backup_retention_daily,
        monthly_retention=settings.backup_retention_monthly,
        backup_dir=str(BACKUP_DIR),
    )
    while not stop_event.is_set():
        try:
            result = _backup_once()
            _log("backup_completed", **result)
        except Exception as exc:
            payload = {
                "status": "error",
                "message": str(exc)[:500],
                "completed_at_epoch_ms": int(time.time() * 1000),
            }
            try:
                database.set_state("backup_status", json.dumps(payload, ensure_ascii=False))
            except Exception:
                pass
            _log("backup_failed", error=str(exc)[:500])
        stop_event.wait(settings.backup_interval_seconds)
    _log("backup_stopped")


if __name__ == "__main__":
    main()
