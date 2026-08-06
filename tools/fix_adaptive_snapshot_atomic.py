from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]

def replace_once(path, old, new):
    p = root / path
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: match={text.count(old)}")
    p.write_text(text.replace(old, new), encoding="utf-8")

p = root / "server/app/db.py"
text = p.read_text(encoding="utf-8")
needle = '''    def get_strategy_weights(self, lottery: str, source: str) -> dict[str, float]:
'''
method = '''    def save_forecast_with_strategies(
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
        probabilities_by_strategy: dict[str, list[float]],
        weights: dict[str, float],
        created_at_epoch_ms: int | None = None,
    ) -> int | None:
        strategy_rows = [
            (strategy, values, max(0.0, float(weights.get(strategy, 0.0))))
            for strategy, values in probabilities_by_strategy.items()
            if len(values) == 10
        ]
        if not strategy_rows:
            raise ValueError("自适应预测缺少有效策略快照")
        if len(strategy_rows) != len(probabilities_by_strategy):
            raise ValueError("部分策略未输出完整10号码概率")

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
            if not cursor.rowcount:
                return None
            forecast_id = int(cursor.lastrowid)
            db.executemany(
                """
                INSERT INTO forecast_strategy_predictions(
                    forecast_id, lottery, source, strategy, probabilities_json,
                    weight_at_prediction, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        forecast_id,
                        lottery,
                        source,
                        strategy,
                        json.dumps(values, separators=(",", ":")),
                        weight,
                        created_at,
                    )
                    for strategy, values, weight in strategy_rows
                ],
            )
            saved = int(
                db.execute(
                    "SELECT COUNT(*) FROM forecast_strategy_predictions WHERE forecast_id = ?",
                    (forecast_id,),
                ).fetchone()[0]
            )
            if saved != len(strategy_rows):
                raise RuntimeError(
                    f"策略快照写入不完整：expected={len(strategy_rows)}, saved={saved}"
                )
            return forecast_id

'''
if text.count(needle) != 1:
    raise SystemExit("db method insertion point missing")
p.write_text(text.replace(needle, method + needle), encoding="utf-8")

replace_once(
    "server/app/service.py",
    '''        inserted = database.save_forecast(
            lottery=spec.key,
            target_period=target_period,
            trained_through_period=trained_through_period,
            position=result.position,
            top6=result.top6,
            top7=result.top7,
            probabilities=result.probabilities,
            source="ai",
            model=result.model,
            analysis=f"{result.analysis} · 云端耗时 {result.latency_ms / 1000:.1f}s",
            risk_note=result.risk_note,
        )
        if inserted is not None:
            database.save_strategy_predictions(
                forecast_id=inserted,
                lottery=spec.key,
                source="ai",
                probabilities_by_strategy=result.strategy_probabilities,
                weights=result.strategy_weights,
            )
            try:
''',
    '''        inserted = database.save_forecast_with_strategies(
            lottery=spec.key,
            target_period=target_period,
            trained_through_period=trained_through_period,
            position=result.position,
            top6=result.top6,
            top7=result.top7,
            probabilities=result.probabilities,
            source="ai",
            model=result.model,
            analysis=f"{result.analysis} · 云端耗时 {result.latency_ms / 1000:.1f}s",
            risk_note=result.risk_note,
            probabilities_by_strategy=result.strategy_probabilities,
            weights=result.strategy_weights,
        )
        if inserted is not None:
            try:
''',
)
replace_once(
    "server/app/service.py",
    '''                    inserted = database.save_forecast(
                        lottery=lottery_key,
                        target_period=next_period,
                        trained_through_period=latest.period,
                        position=selected.position,
                        top6=selected.top6,
                        top7=selected.top7,
                        probabilities=selected.probabilities,
                        source="native",
                        model=native_model,
                        analysis=native.analysis,
                        risk_note=native.risk_note,
                    )
                    if inserted is not None:
                        database.save_strategy_predictions(
                            forecast_id=inserted,
                            lottery=lottery_key,
                            source="native",
                            probabilities_by_strategy=selected.strategy_probabilities,
                            weights=selected.strategy_weights,
                        )
                        generated.append("native")
''',
    '''                    inserted = database.save_forecast_with_strategies(
                        lottery=lottery_key,
                        target_period=next_period,
                        trained_through_period=latest.period,
                        position=selected.position,
                        top6=selected.top6,
                        top7=selected.top7,
                        probabilities=selected.probabilities,
                        source="native",
                        model=native_model,
                        analysis=native.analysis,
                        risk_note=native.risk_note,
                        probabilities_by_strategy=selected.strategy_probabilities,
                        weights=selected.strategy_weights,
                    )
                    if inserted is not None:
                        generated.append("native")
''',
)

test = root / "server/tests/test_adaptive_snapshot_atomic.py"
test.write_text('''from __future__ import annotations

import sqlite3
import tempfile
import unittest

from app.db import Database


class AdaptiveSnapshotAtomicTests(unittest.TestCase):
    def call(self, database: Database, *, strategies):
        return database.save_forecast_with_strategies(
            lottery="xyft",
            target_period="300001",
            trained_through_period="300000",
            position=0,
            top6=[1,2,3,4,5,6],
            top7=[1,2,3,4,5,6,7],
            probabilities=[0.1] * 10,
            source="native",
            model="atomic-v1",
            analysis="atomic",
            risk_note="test",
            probabilities_by_strategy=strategies,
            weights={name: 1 / max(1, len(strategies)) for name in strategies},
        )

    def test_forecast_and_all_strategy_snapshots_commit_together(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/atomic.db")
            forecast_id = self.call(
                db,
                strategies={"a": [0.1] * 10, "b": [0.05] * 9 + [0.55]},
            )
            self.assertIsNotNone(forecast_id)
            with db.connection() as connection:
                forecast_count = connection.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]
                snapshot_count = connection.execute(
                    "SELECT COUNT(*) FROM forecast_strategy_predictions WHERE forecast_id = ?",
                    (forecast_id,),
                ).fetchone()[0]
            self.assertEqual(forecast_count, 1)
            self.assertEqual(snapshot_count, 2)

    def test_invalid_snapshot_rolls_back_forecast(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/rollback.db")
            with self.assertRaises(ValueError):
                self.call(db, strategies={"broken": [0.1] * 9})
            with db.connection() as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0], 0)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM forecast_strategy_predictions").fetchone()[0], 0)

    def test_database_error_rolls_back_main_forecast(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/failure.db")
            with db.connection() as connection:
                connection.execute("DROP TABLE forecast_strategy_predictions")
            with self.assertRaises(sqlite3.OperationalError):
                self.call(db, strategies={"a": [0.1] * 10})
            with db.connection() as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")
print("atomic adaptive snapshot fix applied")
