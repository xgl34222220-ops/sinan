from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, got {count}")
    target.write_text(text.replace(old, new), encoding="utf-8")


def regex_once(path: str, pattern: str, replacement: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{path}: regex expected one match, got {count}")
    target.write_text(updated, encoding="utf-8")


replace_once(
    "server/app/service.py",
    'SERVICE_VERSION = "1.7.1"',
    'SERVICE_VERSION = "1.7.2"',
)
replace_once(
    "server/app/service.py",
    'native_model = "tianji-native-cloud-v3"',
    'native_model = "tianji-native-cloud-v4"',
)
replace_once(
    "server/app/service.py",
    '''    heartbeat = {
        "started_at_epoch_ms": started,''',
    '''    heartbeat = {
        "service_version": SERVICE_VERSION,
        "started_at_epoch_ms": started,''',
)

replace_once(
    "server/app/worker.py",
    "from .service import run_all_cycles  # noqa: E402",
    "from .service import SERVICE_VERSION, run_all_cycles  # noqa: E402",
)
replace_once(
    "server/app/worker.py",
    '''        "worker_started",
        poll_seconds=settings.poll_seconds,''',
    '''        "worker_started",
        service_version=SERVICE_VERSION,
        runtime_revision=os.getenv("TIANJI_RUNTIME_REVISION", ""),
        poll_seconds=settings.poll_seconds,''',
)

replace_once(
    "server/app/main.py",
    '''        "learning": {
            "native": database.strategy_learning_summary(key, "native"),
            "ai": database.strategy_learning_summary(key, "ai"),
        },
    }''',
    '''        "learning": {
            "native": database.strategy_learning_summary(key, "native"),
            "ai": database.strategy_learning_summary(key, "ai"),
        },
        "learning_diagnostics": database.strategy_snapshot_diagnostics(key),
    }''',
)
replace_once(
    "server/app/main.py",
    '''def public_overview() -> dict[str, Any]:
    runtime_ai = load_ai_config()
    registry = load_ai_registry()
    return {
        "health": health_value().model_dump(),''',
    '''def public_overview() -> dict[str, Any]:
    runtime_ai = load_ai_config()
    registry = load_ai_registry()
    heartbeat = _decode_state("worker_heartbeat") or {}
    return {
        "health": health_value().model_dump(),
        "worker": {
            "service_version": heartbeat.get("service_version"),
            "completed_at_epoch_ms": heartbeat.get("completed_at_epoch_ms"),
            "errors": heartbeat.get("errors") or {},
        },''',
)

replace_once(
    "server/app/db.py",
    '''        if not rows:
            return

        metrics: dict[str, dict[str, float | bool]] = {}''',
    '''        if not rows:
            if model == "tianji-native-cloud-v4":
                raise RuntimeError(
                    f"自适应 v4 预测缺少策略快照：forecast_id={forecast_id}"
                )
            return

        metrics: dict[str, dict[str, float | bool]] = {}''',
)
replace_once(
    "server/app/db.py",
    '''        source: str,
        actual_number: int,
        settled_at: int,
    ) -> None:''',
    '''        source: str,
        model: str,
        actual_number: int,
        settled_at: int,
    ) -> None:''',
)
replace_once(
    "server/app/db.py",
    '''                SELECT id, target_period, position_index, top6_json, top7_json, source
                FROM forecasts''',
    '''                SELECT id, target_period, position_index, top6_json, top7_json,
                       source, model
                FROM forecasts''',
)
replace_once(
    "server/app/db.py",
    '''                    source=str(row["source"]),
                    actual_number=actual,''',
    '''                    source=str(row["source"]),
                    model=str(row["model"]),
                    actual_number=actual,''',
)

insert_point = '''    def strategy_learning_summary(self, lottery: str, source: str) -> list[dict[str, object]]:
'''
diagnostics_method = '''    def strategy_snapshot_diagnostics(
        self,
        lottery: str,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        safe_limit = max(1, min(30, int(limit)))
        with self.connection() as db:
            rows = db.execute(
                """
                SELECT
                    f.id AS forecast_id,
                    f.target_period,
                    f.source,
                    f.model,
                    f.actual_number,
                    f.created_at,
                    COUNT(s.strategy) AS snapshot_count,
                    COALESCE(SUM(CASE WHEN s.settled_at IS NOT NULL THEN 1 ELSE 0 END), 0)
                        AS settled_snapshot_count
                FROM forecasts f
                LEFT JOIN forecast_strategy_predictions s ON s.forecast_id = f.id
                WHERE f.lottery = ?
                GROUP BY f.id
                ORDER BY f.created_at DESC, f.id DESC
                LIMIT ?
                """,
                (lottery, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]

'''
replace_once("server/app/db.py", insert_point, diagnostics_method + insert_point)

replace_once(
    "docker-compose.yml",
    '''    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./backups:/app/backups:ro''',
    '''    env_file:
      - .env
    environment:
      TIANJI_RUNTIME_REVISION: "1.7.2-adaptive-v4"
    volumes:
      - ./data:/app/data
      - ./backups:/app/backups:ro''',
)
replace_once(
    "docker-compose.yml",
    '''    env_file:
      - .env
    volumes:
      - ./data:/app/data
    depends_on:
      api:''',
    '''    env_file:
      - .env
    environment:
      TIANJI_RUNTIME_REVISION: "1.7.2-adaptive-v4"
    volumes:
      - ./data:/app/data
    depends_on:
      api:''',
)

(ROOT / "server/tests/test_adaptive_worker_runtime.py").write_text(
    '''from __future__ import annotations

import json
import tempfile
import unittest

from app.db import Database
from app.models import DrawModel
from app.service import SERVICE_VERSION


class AdaptiveWorkerRuntimeTests(unittest.TestCase):
    def test_service_version_marks_forced_worker_runtime(self) -> None:
        self.assertEqual(SERVICE_VERSION, "1.7.2")

    def test_v4_forecast_requires_strategy_snapshot_on_settlement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(f"{directory}/missing.db")
            forecast_id = database.save_forecast(
                lottery="xyft",
                target_period="400001",
                trained_through_period="400000",
                position=0,
                top6=[1, 2, 3, 4, 5, 6],
                top7=[1, 2, 3, 4, 5, 6, 7],
                probabilities=[0.1] * 10,
                source="native",
                model="tianji-native-cloud-v4",
                analysis="missing snapshot",
                risk_note="test",
            )
            self.assertIsNotNone(forecast_id)
            database.save_draws([
                DrawModel(
                    lottery="xyft",
                    period="400001",
                    numbers=[1,2,3,4,5,6,7,8,9,10],
                )
            ])
            with self.assertRaisesRegex(RuntimeError, "缺少策略快照"):
                database.settle_forecasts("xyft")
            record = database.list_forecasts("xyft", 1)[0]
            self.assertIsNone(record.actual_number)

    def test_v4_atomic_snapshot_settles_and_updates_learning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(f"{directory}/v4.db")
            forecast_id = database.save_forecast_with_strategies(
                lottery="xyft",
                target_period="400002",
                trained_through_period="400001",
                position=0,
                top6=[1,2,3,4,5,6],
                top7=[1,2,3,4,5,6,7],
                probabilities=[0.1] * 10,
                source="native",
                model="tianji-native-cloud-v4",
                analysis="v4",
                risk_note="test",
                probabilities_by_strategy={
                    "good": [0.7] + [0.3 / 9] * 9,
                    "bad": [0.3 / 9] * 9 + [0.7],
                },
                weights={"good": 0.5, "bad": 0.5},
            )
            self.assertIsNotNone(forecast_id)
            diagnostics = database.strategy_snapshot_diagnostics("xyft")
            self.assertEqual(diagnostics[0]["snapshot_count"], 2)
            database.save_draws([
                DrawModel(
                    lottery="xyft",
                    period="400002",
                    numbers=[1,2,3,4,5,6,7,8,9,10],
                )
            ])
            self.assertEqual(database.settle_forecasts("xyft"), 1)
            learning = database.strategy_learning_summary("xyft", "native")
            self.assertEqual({row["samples"] for row in learning}, {1})
            self.assertGreater(
                next(row["weight"] for row in learning if row["strategy"] == "good"),
                next(row["weight"] for row in learning if row["strategy"] == "bad"),
            )
            diagnostics = database.strategy_snapshot_diagnostics("xyft")
            self.assertEqual(diagnostics[0]["settled_snapshot_count"], 2)


if __name__ == "__main__":
    unittest.main()
''',
    encoding="utf-8",
)

print("adaptive worker runtime v1.7.2 changes applied")
