from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]

runtime_path = root / "server/app/runtime_optimizations.py"
runtime_text = runtime_path.read_text(encoding="utf-8")
pattern = re.compile(
    r"def _batch_settle_forecasts\(self: Database, lottery: str\) -> int:\n.*?(?=\n\ndef ensure_runtime_indexes)",
    re.S,
)
replacement = '''def _batch_settle_forecasts(self: Database, lottery: str) -> int:
    """Delegate to the canonical learning-aware settlement implementation.

    This hook used to replace ``Database.settle_forecasts`` with a faster legacy
    query that only settled the forecast row. That silently skipped strategy
    snapshots and prevented online learning. Keep the hook for compatibility,
    but make the canonical database method the single source of truth.
    """
    return Database.settle_forecasts(self, lottery)
'''
new_runtime, count = pattern.subn(replacement, runtime_text)
if count != 1:
    raise SystemExit(f"runtime replacement count={count}")
runtime_path.write_text(new_runtime, encoding="utf-8")

service_path = root / "server/app/service.py"
service_text = service_path.read_text(encoding="utf-8")
service_text = service_text.replace('SERVICE_VERSION = "1.7.3"', 'SERVICE_VERSION = "1.7.4"')
service_path.write_text(service_text, encoding="utf-8")

compose_path = root / "docker-compose.yml"
compose_text = compose_path.read_text(encoding="utf-8")
compose_text = compose_text.replace('TIANJI_RUNTIME_REVISION: "1.7.3-learning-reconcile"', 'TIANJI_RUNTIME_REVISION: "1.7.4-learning-settlement"')
compose_path.write_text(compose_text, encoding="utf-8")

runtime_test_path = root / "server/tests/test_runtime_optimizations.py"
runtime_test_text = runtime_test_path.read_text(encoding="utf-8")
anchor = '\n\nif __name__ == "__main__":\n'
new_test = '''
    def test_runtime_hook_reconciles_learning_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(str(Path(directory) / "learning.db"))
            forecast_id = database.save_forecast_with_strategies(
                lottery="xyft",
                target_period="202608050101",
                trained_through_period="202608050100",
                position=0,
                top6=[1, 2, 3, 4, 5, 6],
                top7=[1, 2, 3, 4, 5, 6, 7],
                probabilities=[0.1] * 10,
                source="native",
                model="tianji-native-cloud-v4",
                analysis="学习补偿测试",
                risk_note="测试",
                probabilities_by_strategy={
                    "good": [0.7] + [0.3 / 9] * 9,
                    "bad": [0.3 / 9] * 9 + [0.7],
                },
                weights={"good": 0.5, "bad": 0.5},
            )
            self.assertIsNotNone(forecast_id)
            with database.connection() as db:
                db.execute(
                    """
                    UPDATE forecasts SET
                        actual_number = 1, top6_hit = 1, top7_hit = 1, settled_at = 123456789
                    WHERE id = ?
                    """,
                    (forecast_id,),
                )

            self.assertEqual(_batch_settle_forecasts(database, "xyft"), 1)
            learning = database.strategy_learning_summary("xyft", "native")
            self.assertEqual({row["samples"] for row in learning}, {1})
            diagnostics = database.strategy_snapshot_diagnostics("xyft")
            self.assertEqual(diagnostics[0]["settled_snapshot_count"], 2)
            self.assertEqual(_batch_settle_forecasts(database, "xyft"), 0)
'''
if anchor not in runtime_test_text:
    raise SystemExit("runtime test anchor missing")
runtime_test_text = runtime_test_text.replace(anchor, "\n" + new_test + anchor)
runtime_test_path.write_text(runtime_test_text, encoding="utf-8")

version_test_path = root / "server/tests/test_adaptive_worker_runtime.py"
version_test_text = version_test_path.read_text(encoding="utf-8")
version_test_text = version_test_text.replace(
    'self.assertEqual(SERVICE_VERSION, "1.7.3")',
    'self.assertEqual(SERVICE_VERSION, "1.7.4")',
)
version_test_path.write_text(version_test_text, encoding="utf-8")
