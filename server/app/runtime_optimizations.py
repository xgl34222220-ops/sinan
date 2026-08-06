from __future__ import annotations

import json
from types import MethodType
from typing import Any

from .config import settings
from .db import Database, database
from .migrations import run_migrations


_INSTALLED = False


def _batch_settle_forecasts(self: Database, lottery: str) -> int:
    """Settle every available forecast in one read and one batch update."""
    with self.connection() as db:
        rows = db.execute(
            """
            SELECT f.id,f.position_index,f.top6_json,f.top7_json,d.numbers_json
            FROM forecasts AS f
            INNER JOIN draws AS d
                ON d.lottery=f.lottery AND d.period=f.target_period
            WHERE f.lottery=? AND f.settled_at IS NULL
            ORDER BY f.id ASC
            """,
            (lottery,),
        ).fetchall()
        if not rows:
            return 0

        import time

        settled_at = int(time.time() * 1000)
        updates: list[tuple[int, int, int, int, int]] = []
        for row in rows:
            numbers = json.loads(row["numbers_json"])
            position = int(row["position_index"])
            if position < 0 or position >= len(numbers):
                continue
            actual = int(numbers[position])
            top6 = set(json.loads(row["top6_json"]))
            top7 = set(json.loads(row["top7_json"]))
            updates.append(
                (actual, int(actual in top6), int(actual in top7), settled_at, int(row["id"]))
            )

        if updates:
            db.executemany(
                """
                UPDATE forecasts SET
                    actual_number=?,top6_hit=?,top7_hit=?,settled_at=?
                WHERE id=? AND settled_at IS NULL
                """,
                updates,
            )
        return len(updates)


def ensure_runtime_indexes() -> None:
    run_migrations()


def cleanup_runtime_state(max_job_age_days: int = 30) -> dict[str, Any]:
    import time

    now = int(time.time() * 1000)
    job_cutoff = now - max(1, max_job_age_days) * 86_400_000
    delivery_cutoff = now - max(1, settings.push_delivery_retention_days) * 86_400_000
    device_cutoff = now - max(7, settings.push_device_stale_days) * 86_400_000
    alert_cutoff = now - max(30, settings.push_delivery_retention_days) * 86_400_000

    with database.connection() as db:
        jobs = db.execute(
            """
            DELETE FROM forecast_jobs
            WHERE updated_at<?
              AND status IN ('completed','duplicate','discarded','skipped')
            """,
            (job_cutoff,),
        )
        deliveries = db.execute(
            "DELETE FROM push_deliveries WHERE attempted_at<?",
            (delivery_cutoff,),
        )
        reads = db.execute(
            """
            DELETE FROM push_alert_reads
            WHERE alert_id IN (SELECT id FROM push_alerts WHERE created_at<?)
            """,
            (alert_cutoff,),
        )
        alerts = db.execute(
            """
            DELETE FROM push_alerts
            WHERE created_at<?
              AND id<=COALESCE((SELECT MIN(read_through_alert_id) FROM push_devices),id)
            """,
            (alert_cutoff,),
        )
        stale_devices = db.execute(
            "DELETE FROM push_devices WHERE last_seen_at<? AND fcm_token=''",
            (device_cutoff,),
        )
        return {
            "forecast_jobs_deleted": max(0, int(jobs.rowcount)),
            "push_deliveries_deleted": max(0, int(deliveries.rowcount)),
            "push_reads_deleted": max(0, int(reads.rowcount)),
            "push_alerts_deleted": max(0, int(alerts.rowcount)),
            "stale_push_devices_deleted": max(0, int(stale_devices.rowcount)),
        }


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    run_migrations()
    database.settle_forecasts = MethodType(_batch_settle_forecasts, database)

    from .push_runtime_v2 import install as install_push_runtime_v2

    install_push_runtime_v2()
    _INSTALLED = True
