from __future__ import annotations

from contextlib import contextmanager
import json
import os
import sqlite3
import time
from typing import Any, Iterable, Iterator

from .config import settings
from .models import DrawModel, ForecastModel


class Database:
    def __init__(self, path: str = settings.database_path) -> None:
        self.path = path
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 20000")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.execute("PRAGMA synchronous = NORMAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS draws (
                    lottery TEXT NOT NULL,
                    period TEXT NOT NULL,
                    numbers_json TEXT NOT NULL,
                    draw_time TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'api68',
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (lottery, period)
                );
                CREATE INDEX IF NOT EXISTS draws_lottery_period
                    ON draws(lottery, period DESC);

                CREATE TABLE IF NOT EXISTS forecasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lottery TEXT NOT NULL,
                    target_period TEXT NOT NULL,
                    trained_through_period TEXT NOT NULL,
                    position_index INTEGER NOT NULL,
                    top6_json TEXT NOT NULL,
                    top7_json TEXT NOT NULL,
                    probabilities_json TEXT NOT NULL,
                    source TEXT NOT NULL,
                    model TEXT NOT NULL,
                    analysis TEXT NOT NULL DEFAULT '',
                    risk_note TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL,
                    actual_number INTEGER,
                    top6_hit INTEGER,
                    top7_hit INTEGER,
                    settled_at INTEGER,
                    UNIQUE(lottery, target_period, source, model, position_index)
                );
                CREATE INDEX IF NOT EXISTS forecasts_lottery_created
                    ON forecasts(lottery, created_at DESC);

                CREATE TABLE IF NOT EXISTS forecast_jobs (
                    lottery TEXT NOT NULL,
                    target_period TEXT NOT NULL,
                    source TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL DEFAULT '',
                    attempts INTEGER NOT NULL DEFAULT 1,
                    claimed_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (lottery, target_period, source)
                );
                CREATE INDEX IF NOT EXISTS forecast_jobs_updated
                    ON forecast_jobs(updated_at DESC);

                CREATE TABLE IF NOT EXISTS service_state (
                    state_key TEXT PRIMARY KEY,
                    state_value TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                """
            )

            # 旧版把模型和名次放进唯一键，导致同一期切换模型或并发运行时
            # 可以写入多条正式 AI 预测。正式档案必须保留最早冻结的一条。
            db.execute(
                """
                DELETE FROM forecasts
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM forecasts
                    GROUP BY lottery, target_period, source
                )
                """
            )
            db.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS forecasts_one_source_per_target
                ON forecasts(lottery, target_period, source)
                """
            )

    def ping(self) -> bool:
        try:
            with self.connection() as db:
                return db.execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False

    def save_draws(self, draws: Iterable[DrawModel]) -> int:
        now = int(time.time() * 1000)
        rows = [
            (
                draw.lottery,
                draw.period,
                json.dumps(draw.numbers, separators=(",", ":")),
                draw.draw_time,
                draw.source,
                now,
            )
            for draw in draws
        ]
        if not rows:
            return 0
        with self.connection() as db:
            before = db.total_changes
            db.executemany(
                """
                INSERT INTO draws(
                    lottery, period, numbers_json, draw_time, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(lottery, period) DO UPDATE SET
                    numbers_json = excluded.numbers_json,
                    draw_time = CASE
                        WHEN excluded.draw_time <> '' THEN excluded.draw_time
                        ELSE draws.draw_time
                    END,
                    source = excluded.source
                """,
                rows,
            )
            return db.total_changes - before

    def list_draws(self, lottery: str, limit: int = 3000) -> list[DrawModel]:
        safe_limit = max(1, min(5000, limit))
        with self.connection() as db:
            rows = db.execute(
                """
                SELECT lottery, period, numbers_json, draw_time, source
                FROM draws
                WHERE lottery = ?
                ORDER BY LENGTH(period) DESC, period DESC
                LIMIT ?
                """,
                (lottery, safe_limit),
            ).fetchall()
        result = [self._row_to_draw(row) for row in rows]
        return list(reversed(result))

    def get_draw(self, lottery: str, period: str) -> DrawModel | None:
        with self.connection() as db:
            row = db.execute(
                """
                SELECT lottery, period, numbers_json, draw_time, source
                FROM draws WHERE lottery = ? AND period = ?
                """,
                (lottery, period),
            ).fetchone()
        return self._row_to_draw(row) if row else None

    def latest_draw(self, lottery: str) -> DrawModel | None:
        draws = self.list_draws(lottery, 1)
        return draws[-1] if draws else None

    def has_forecast(
        self,
        lottery: str,
        target_period: str,
        source: str,
        model: str | None = None,
    ) -> bool:
        # model 参数仅为兼容旧调用；正式档案按彩种、目标期、来源唯一。
        with self.connection() as db:
            row = db.execute(
                """
                SELECT 1 FROM forecasts
                WHERE lottery = ? AND target_period = ? AND source = ?
                LIMIT 1
                """,
                (lottery, target_period, source),
            ).fetchone()
        return row is not None

    def claim_forecast_job(
        self,
        *,
        lottery: str,
        target_period: str,
        source: str,
        model: str,
        lease_ms: int,
        retry_after_ms: int = 30_000,
    ) -> bool:
        """跨进程原子领取预测任务，防止 API 与 Worker 重复调用同一期。"""
        now = int(time.time() * 1000)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            frozen = db.execute(
                """
                SELECT 1 FROM forecasts
                WHERE lottery = ? AND target_period = ? AND source = ?
                LIMIT 1
                """,
                (lottery, target_period, source),
            ).fetchone()
            if frozen is not None:
                return False

            row = db.execute(
                """
                SELECT status, updated_at, attempts
                FROM forecast_jobs
                WHERE lottery = ? AND target_period = ? AND source = ?
                """,
                (lottery, target_period, source),
            ).fetchone()
            if row is None:
                db.execute(
                    """
                    INSERT INTO forecast_jobs(
                        lottery, target_period, source, model, status,
                        message, attempts, claimed_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'queued', '', 1, ?, ?)
                    """,
                    (lottery, target_period, source, model, now, now),
                )
                return True

            status = str(row["status"])
            age_ms = max(0, now - int(row["updated_at"]))
            if status in {"queued", "running"} and age_ms < lease_ms:
                return False
            if status == "completed":
                return False
            if status == "error" and age_ms < retry_after_ms:
                return False
            if status == "discarded":
                return False

            db.execute(
                """
                UPDATE forecast_jobs SET
                    model = ?, status = 'queued', message = '',
                    attempts = attempts + 1, claimed_at = ?, updated_at = ?
                WHERE lottery = ? AND target_period = ? AND source = ?
                """,
                (model, now, now, lottery, target_period, source),
            )
            return True

    def finish_forecast_job(
        self,
        *,
        lottery: str,
        target_period: str,
        source: str,
        status: str,
        message: str = "",
        model: str | None = None,
    ) -> None:
        now = int(time.time() * 1000)
        with self.connection() as db:
            if model is None:
                db.execute(
                    """
                    UPDATE forecast_jobs SET status = ?, message = ?, updated_at = ?
                    WHERE lottery = ? AND target_period = ? AND source = ?
                    """,
                    (status, message[:500], now, lottery, target_period, source),
                )
            else:
                db.execute(
                    """
                    UPDATE forecast_jobs SET
                        model = ?, status = ?, message = ?, updated_at = ?
                    WHERE lottery = ? AND target_period = ? AND source = ?
                    """,
                    (model, status, message[:500], now, lottery, target_period, source),
                )

    def get_forecast_job(self, lottery: str, source: str = "ai") -> dict[str, Any] | None:
        with self.connection() as db:
            row = db.execute(
                """
                SELECT lottery, target_period, source, model, status,
                       message, attempts, claimed_at, updated_at
                FROM forecast_jobs
                WHERE lottery = ? AND source = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (lottery, source),
            ).fetchone()
        return dict(row) if row is not None else None

    def save_forecast(
        self,
        *,
        lottery: str,
        target_period: str,
        trained_through_period: str,
        position: int,
        top6: list[int],
        top7: list[int],
        probabilities: list[float],
        source: str,
        model: str,
        analysis: str,
        risk_note: str,
        created_at_epoch_ms: int | None = None,
    ) -> int | None:
        created_at = created_at_epoch_ms or int(time.time() * 1000)
        with self.connection() as db:
            cursor = db.execute(
                """
                INSERT OR IGNORE INTO forecasts(
                    lottery, target_period, trained_through_period,
                    position_index, top6_json, top7_json, probabilities_json,
                    source, model, analysis, risk_note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lottery,
                    target_period,
                    trained_through_period,
                    position,
                    json.dumps(top6, separators=(",", ":")),
                    json.dumps(top7, separators=(",", ":")),
                    json.dumps(probabilities, separators=(",", ":")),
                    source,
                    model,
                    analysis,
                    risk_note,
                    created_at,
                ),
            )
            return int(cursor.lastrowid) if cursor.rowcount else None

    def settle_forecasts(self, lottery: str) -> int:
        with self.connection() as db:
            pending = db.execute(
                """
                SELECT id, target_period, position_index, top6_json, top7_json
                FROM forecasts
                WHERE lottery = ? AND settled_at IS NULL
                ORDER BY id ASC
                """,
                (lottery,),
            ).fetchall()
            settled = 0
            now = int(time.time() * 1000)
            for row in pending:
                draw = db.execute(
                    "SELECT numbers_json FROM draws WHERE lottery = ? AND period = ?",
                    (lottery, row["target_period"]),
                ).fetchone()
                if draw is None:
                    continue
                numbers = json.loads(draw["numbers_json"])
                position = int(row["position_index"])
                if position < 0 or position >= len(numbers):
                    continue
                actual = int(numbers[position])
                top6 = set(json.loads(row["top6_json"]))
                top7 = set(json.loads(row["top7_json"]))
                db.execute(
                    """
                    UPDATE forecasts SET
                        actual_number = ?, top6_hit = ?, top7_hit = ?, settled_at = ?
                    WHERE id = ?
                    """,
                    (actual, int(actual in top6), int(actual in top7), now, row["id"]),
                )
                settled += 1
            return settled

    def list_forecasts(self, lottery: str, limit: int = 100) -> list[ForecastModel]:
        safe_limit = max(1, min(500, limit))
        with self.connection() as db:
            rows = db.execute(
                """
                SELECT * FROM forecasts
                WHERE lottery = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (lottery, safe_limit),
            ).fetchall()
        return [self._row_to_forecast(row) for row in rows]

    def latest_forecasts(self, lottery: str) -> list[ForecastModel]:
        with self.connection() as db:
            row = db.execute(
                """
                SELECT target_period FROM forecasts
                WHERE lottery = ?
                ORDER BY created_at DESC, id DESC LIMIT 1
                """,
                (lottery,),
            ).fetchone()
            if row is None:
                return []
            rows = db.execute(
                """
                SELECT * FROM forecasts
                WHERE lottery = ? AND target_period = ?
                ORDER BY created_at DESC, id DESC
                """,
                (lottery, row["target_period"]),
            ).fetchall()
        return [self._row_to_forecast(item) for item in rows]

    def set_state(self, key: str, value: str) -> None:
        with self.connection() as db:
            db.execute(
                """
                INSERT INTO service_state(state_key, state_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    state_value = excluded.state_value,
                    updated_at = excluded.updated_at
                """,
                (key, value, int(time.time() * 1000)),
            )

    def get_state(self, key: str) -> tuple[str, int] | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT state_value, updated_at FROM service_state WHERE state_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return str(row["state_value"]), int(row["updated_at"])

    def delete_state(self, key: str) -> None:
        with self.connection() as db:
            db.execute("DELETE FROM service_state WHERE state_key = ?", (key,))

    @staticmethod
    def _row_to_draw(row: sqlite3.Row) -> DrawModel:
        return DrawModel(
            lottery=row["lottery"],
            period=row["period"],
            numbers=json.loads(row["numbers_json"]),
            draw_time=row["draw_time"],
            source=row["source"],
        )

    @staticmethod
    def _row_to_forecast(row: sqlite3.Row) -> ForecastModel:
        return ForecastModel(
            id=int(row["id"]),
            lottery=row["lottery"],
            target_period=row["target_period"],
            trained_through_period=row["trained_through_period"],
            position=int(row["position_index"]),
            top6=json.loads(row["top6_json"]),
            top7=json.loads(row["top7_json"]),
            probabilities=json.loads(row["probabilities_json"]),
            source=row["source"],
            model=row["model"],
            analysis=row["analysis"],
            risk_note=row["risk_note"],
            created_at_epoch_ms=int(row["created_at"]),
            actual_number=row["actual_number"],
            top6_hit=None if row["top6_hit"] is None else bool(row["top6_hit"]),
            top7_hit=None if row["top7_hit"] is None else bool(row["top7_hit"]),
        )


database = Database()
