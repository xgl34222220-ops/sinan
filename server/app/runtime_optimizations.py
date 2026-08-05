from __future__ import annotations

import json
from types import MethodType
from typing import Any

from .db import Database, database


_INSTALLED = False


def _batch_settle_forecasts(self: Database, lottery: str) -> int:
    """Settle every available forecast in one read and one batch update."""
    with self.connection() as db:
        rows = db.execute(
            """
            SELECT
                f.id,
                f.position_index,
                f.top6_json,
                f.top7_json,
                d.numbers_json
            FROM forecasts AS f
            INNER JOIN draws AS d
                ON d.lottery = f.lottery
               AND d.period = f.target_period
            WHERE f.lottery = ?
              AND f.settled_at IS NULL
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
                (
                    actual,
                    int(actual in top6),
                    int(actual in top7),
                    settled_at,
                    int(row["id"]),
                )
            )

        if updates:
            db.executemany(
                """
                UPDATE forecasts SET
                    actual_number = ?,
                    top6_hit = ?,
                    top7_hit = ?,
                    settled_at = ?
                WHERE id = ?
                  AND settled_at IS NULL
                """,
                updates,
            )
        return len(updates)


def ensure_runtime_indexes() -> None:
    with database.connection() as db:
        db.executescript(
            """
            CREATE INDEX IF NOT EXISTS forecasts_unsettled_target
                ON forecasts(lottery, settled_at, target_period);
            CREATE INDEX IF NOT EXISTS forecasts_source_status
                ON forecasts(source, settled_at, created_at DESC);
            CREATE INDEX IF NOT EXISTS forecast_jobs_status_updated
                ON forecast_jobs(status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS service_state_updated
                ON service_state(updated_at DESC);
            """
        )


def cleanup_runtime_state(max_job_age_days: int = 30) -> dict[str, Any]:
    import time

    cutoff = int(time.time() * 1000) - max(1, max_job_age_days) * 86_400_000
    with database.connection() as db:
        cursor = db.execute(
            """
            DELETE FROM forecast_jobs
            WHERE updated_at < ?
              AND status IN ('completed', 'duplicate', 'discarded', 'skipped')
            """,
            (cutoff,),
        )
        return {"forecast_jobs_deleted": max(0, int(cursor.rowcount))}


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ensure_runtime_indexes()
    database.settle_forecasts = MethodType(_batch_settle_forecasts, database)
    _INSTALLED = True
