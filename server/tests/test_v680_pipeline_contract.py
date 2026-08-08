from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server" / "app"


class V680PipelineContractTests(unittest.TestCase):
    def test_realtime_endpoint_exposes_pipeline_percentiles(self) -> None:
        source = (SERVER / "realtime_admin.py").read_text(encoding="utf-8")
        for field in (
            '"detection_delay_p50_ms"',
            '"detection_delay_p95_ms"',
            '"settlement_latency_p50_ms"',
            '"settlement_latency_p95_ms"',
            '"push_p50_ms"',
            '"push_p95_ms"',
            '"telegram_p50_ms"',
            '"telegram_p95_ms"',
            '"full_cycle_p50_ms"',
            '"full_cycle_p95_ms"',
        ):
            self.assertIn(field, source)

    def test_worker_persists_delivery_and_full_cycle_metrics(self) -> None:
        source = (SERVER / "realtime_worker.py").read_text(encoding="utf-8")
        self.assertIn('_set_state(f"notify:{lottery_key}"', source)
        self.assertIn('_set_state("full_cycle_metrics"', source)
        self.assertIn('"delivery_p95_ms"', source)
        self.assertIn('"duration_p95_ms"', source)
        self.assertIn('"worker_mode": "realtime-split-lane-v68"', source)

    def test_console_renders_four_stage_pipeline(self) -> None:
        source = (SERVER / "console_final_polish.py").read_text(encoding="utf-8")
        self.assertIn("v68-pipeline", source)
        self.assertIn("开奖发现", source)
        self.assertIn("写库结算", source)
        self.assertIn("App/FCM 投递", source)
        self.assertIn("完整预测周期", source)
        self.assertIn("P50", source)
        self.assertIn("P95", source)


if __name__ == "__main__":
    unittest.main()
