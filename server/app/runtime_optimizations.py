from __future__ import annotations

import json
from types import MethodType
from typing import Any

from .config import settings
from .db import Database, database
from .migrations import run_migrations


_INSTALLED = False


def _batch_settle_forecasts(self: Database, lottery: str) -> int:
    """Delegate to the canonical learning-aware settlement implementation.

    This hook used to replace ``Database.settle_forecasts`` with a faster legacy
    query that only settled the forecast row. That silently skipped strategy
    snapshots and prevented online learning. Keep the hook for compatibility,
    but make the canonical database method the single source of truth.
    """
    return Database.settle_forecasts(self, lottery)


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
        stale_devices = db.execute(
            "DELETE FROM push_devices WHERE last_seen_at<?",
            (device_cutoff,),
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
    from .push_runtime_bridge import install as install_push_runtime_bridge
    from .push_runtime_fixes import install as install_push_runtime_fixes
    from .push_freshness_guard import install as install_push_freshness_guard

    install_push_runtime_v2()
    install_push_runtime_bridge()
    install_push_runtime_fixes()
    install_push_freshness_guard()
    _INSTALLED = True
