from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]

db_path = root / "server/app/db.py"
db_text = db_path.read_text(encoding="utf-8")
pattern = re.compile(
    r"    def settle_forecasts\(self, lottery: str\) -> int:\n.*?(?=    def list_forecasts\()",
    re.S,
)
replacement = '''    def settle_forecasts(self, lottery: str) -> int:
        with self.connection() as db:
            pending = db.execute(
                """
                SELECT f.id, f.target_period, f.position_index, f.top6_json,
                       f.top7_json, f.source, f.model, f.actual_number, f.settled_at
                FROM forecasts f
                WHERE f.lottery = ?
                  AND (
                      f.settled_at IS NULL
                      OR EXISTS (
                          SELECT 1
                          FROM forecast_strategy_predictions s
                          WHERE s.forecast_id = f.id AND s.settled_at IS NULL
                      )
                  )
                ORDER BY f.id ASC
                """,
                (lottery,),
            ).fetchall()
            settled = 0
            now = int(time.time() * 1000)
            for row in pending:
                actual_value = row["actual_number"]
                if actual_value is None:
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
                else:
                    # 兼容旧 Worker 已经结算主预测、但没有结算策略快照的残缺记录。
                    # 只要仍存在未结算快照，就用已冻结的 actual_number 补算损失和权重。
                    actual = int(actual_value)

                self._settle_strategy_learning(
                    db,
                    forecast_id=int(row["id"]),
                    lottery=lottery,
                    source=str(row["source"]),
                    model=str(row["model"]),
                    actual_number=actual,
                    settled_at=now,
                )
                settled += 1
            return settled

'''
new_db_text, count = pattern.subn(replacement, db_text)
if count != 1:
    raise SystemExit(f"settle_forecasts replacement count={count}")
db_path.write_text(new_db_text, encoding="utf-8")

service_path = root / "server/app/service.py"
service_text = service_path.read_text(encoding="utf-8")
service_text = service_text.replace('SERVICE_VERSION = "1.7.2"', 'SERVICE_VERSION = "1.7.3"')
service_path.write_text(service_text, encoding="utf-8")

compose_path = root / "docker-compose.yml"
compose_text = compose_path.read_text(encoding="utf-8")
compose_text = compose_text.replace('TIANJI_RUNTIME_REVISION: "1.7.2-adaptive-v4"', 'TIANJI_RUNTIME_REVISION: "1.7.3-learning-reconcile"')
compose_path.write_text(compose_text, encoding="utf-8")

test_path = root / "server/tests/test_adaptive_worker_runtime.py"
test_text = test_path.read_text(encoding="utf-8")
test_text = test_text.replace('self.assertEqual(SERVICE_VERSION, "1.7.2")', 'self.assertEqual(SERVICE_VERSION, "1.7.3")')
anchor = '\n\nif __name__ == "__main__":\n'
new_test = '''
    def test_reconciles_snapshots_after_legacy_forecast_settlement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(f"{directory}/reconcile.db")
            forecast_id = database.save_forecast_with_strategies(
                lottery="xyft",
                target_period="400003",
                trained_through_period="400002",
                position=0,
                top6=[1,2,3,4,5,6],
                top7=[1,2,3,4,5,6,7],
                probabilities=[0.1] * 10,
                source="native",
                model="tianji-native-cloud-v4",
                analysis="reconcile",
                risk_note="test",
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

            before = database.strategy_snapshot_diagnostics("xyft")[0]
            self.assertEqual(before["snapshot_count"], 2)
            self.assertEqual(before["settled_snapshot_count"], 0)

            self.assertEqual(database.settle_forecasts("xyft"), 1)
            learning = database.strategy_learning_summary("xyft", "native")
            self.assertEqual({row["samples"] for row in learning}, {1})
            self.assertGreater(
                next(row["weight"] for row in learning if row["strategy"] == "good"),
                next(row["weight"] for row in learning if row["strategy"] == "bad"),
            )
            after = database.strategy_snapshot_diagnostics("xyft")[0]
            self.assertEqual(after["settled_snapshot_count"], 2)
            self.assertEqual(database.settle_forecasts("xyft"), 0)
'''
if anchor not in test_text:
    raise SystemExit("test anchor missing")
test_text = test_text.replace(anchor, "\n" + new_test + anchor)
test_path.write_text(test_text, encoding="utf-8")
