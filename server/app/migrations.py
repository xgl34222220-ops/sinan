from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Callable

from .db import Database, database


logger = logging.getLogger("tianji.migrations")
Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in db.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_column(db: sqlite3.Connection, table: str, definition: str) -> None:
    name = definition.split(maxsplit=1)[0]
    if name not in _columns(db, table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _migration_001_push_protocol_v2(db: sqlite3.Connection) -> None:
    now = int(time.time() * 1000)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS push_devices (
            installation_id TEXT PRIMARY KEY,
            secret_hash TEXT NOT NULL,
            fcm_token TEXT NOT NULL DEFAULT '',
            platform TEXT NOT NULL DEFAULT 'android',
            app_version TEXT NOT NULL DEFAULT '',
            device_name TEXT NOT NULL DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 1,
            xyft_enabled INTEGER NOT NULL DEFAULT 1,
            azxy10_enabled INTEGER NOT NULL DEFAULT 1,
            ai_enabled INTEGER NOT NULL DEFAULT 1,
            native_enabled INTEGER NOT NULL DEFAULT 1,
            escalation_enabled INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            last_seen_at INTEGER NOT NULL,
            read_through_alert_id INTEGER NOT NULL DEFAULT 0,
            protocol_version INTEGER NOT NULL DEFAULT 2
        );

        CREATE TABLE IF NOT EXISTS push_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_key TEXT NOT NULL UNIQUE,
            lottery TEXT NOT NULL,
            lottery_name TEXT NOT NULL,
            source TEXT NOT NULL,
            source_name TEXT NOT NULL,
            model TEXT NOT NULL,
            streak INTEGER NOT NULL,
            threshold INTEGER NOT NULL,
            latest_target_period TEXT NOT NULL,
            recent_periods_json TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            schema_version INTEGER NOT NULL DEFAULT 2,
            event_type TEXT NOT NULL DEFAULT 'miss_alert',
            severity TEXT NOT NULL DEFAULT 'warning',
            deep_link TEXT NOT NULL DEFAULT '',
            collapse_key TEXT NOT NULL DEFAULT '',
            expires_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS push_alert_reads (
            alert_id INTEGER NOT NULL,
            installation_id TEXT NOT NULL,
            read_at INTEGER NOT NULL,
            PRIMARY KEY(alert_id, installation_id)
        );

        CREATE TABLE IF NOT EXISTS push_deliveries (
            alert_id INTEGER NOT NULL,
            installation_id TEXT NOT NULL,
            status TEXT NOT NULL,
            response_code INTEGER,
            message TEXT NOT NULL DEFAULT '',
            attempted_at INTEGER NOT NULL,
            PRIMARY KEY(alert_id, installation_id)
        );

        CREATE INDEX IF NOT EXISTS push_devices_last_seen
            ON push_devices(last_seen_at DESC);
        CREATE INDEX IF NOT EXISTS push_devices_token_active
            ON push_devices(enabled, fcm_token, last_seen_at DESC);
        CREATE INDEX IF NOT EXISTS push_alerts_created
            ON push_alerts(created_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS push_alert_reads_installation
            ON push_alert_reads(installation_id, alert_id DESC);
        CREATE INDEX IF NOT EXISTS push_deliveries_status_attempted
            ON push_deliveries(status, attempted_at, alert_id);
        """
    )

    _add_column(db, "push_devices", "read_through_alert_id INTEGER NOT NULL DEFAULT 0")
    _add_column(db, "push_devices", "protocol_version INTEGER NOT NULL DEFAULT 2")
    _add_column(db, "push_alerts", "schema_version INTEGER NOT NULL DEFAULT 2")
    _add_column(db, "push_alerts", "event_type TEXT NOT NULL DEFAULT 'miss_alert'")
    _add_column(db, "push_alerts", "severity TEXT NOT NULL DEFAULT 'warning'")
    _add_column(db, "push_alerts", "deep_link TEXT NOT NULL DEFAULT ''")
    _add_column(db, "push_alerts", "collapse_key TEXT NOT NULL DEFAULT ''")
    _add_column(db, "push_alerts", "expires_at INTEGER")

    db.executescript(
        """
        CREATE INDEX IF NOT EXISTS push_alerts_delivery_window
            ON push_alerts(expires_at, created_at DESC, id DESC);
        """
    )

    db.execute(
        """
        UPDATE push_devices
        SET protocol_version=2
        WHERE protocol_version IS NULL OR protocol_version<2
        """
    )
    db.execute(
        """
        UPDATE push_alerts
        SET
            schema_version=2,
            event_type=CASE
                WHEN streak<=2 THEN 'miss_prealert'
                WHEN streak=threshold THEN 'miss_alert'
                ELSE 'miss_escalation'
            END,
            severity=CASE
                WHEN streak<=2 THEN 'info'
                WHEN streak=threshold THEN 'warning'
                ELSE 'critical'
            END,
            collapse_key=CASE
                WHEN collapse_key='' THEN lottery || ':' || source || ':' || model
                ELSE collapse_key
            END,
            expires_at=COALESCE(expires_at, created_at + 259200000)
        WHERE schema_version<2 OR collapse_key='' OR expires_at IS NULL
        """
    )

    db.execute(
        """
        INSERT INTO service_state(state_key,state_value,updated_at)
        VALUES('schema_upgrade_v2', ?, ?)
        ON CONFLICT(state_key) DO UPDATE SET
            state_value=excluded.state_value,
            updated_at=excluded.updated_at
        """,
        (str(now), now),
    )


def _migration_002_runtime_indexes(db: sqlite3.Connection) -> None:
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


MIGRATIONS: tuple[Migration, ...] = (
    (1, "push protocol v2 and read cursor", _migration_001_push_protocol_v2),
    (2, "runtime indexes", _migration_002_runtime_indexes),
)


def run_migrations(target: Database = database) -> list[int]:
    applied: list[int] = []
    with target.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at INTEGER NOT NULL
            )
            """
        )
        completed = {
            int(row["version"])
            for row in db.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for version, name, migration in MIGRATIONS:
            if version in completed:
                continue
            migration(db)
            db.execute(
                "INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",
                (version, name, int(time.time() * 1000)),
            )
            applied.append(version)
            logger.info("applied migration %s: %s", version, name)
    return applied
