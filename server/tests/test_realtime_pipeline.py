from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server" / "app"
APP = ROOT / "app" / "src" / "main" / "java" / "com" / "tianji" / "probabilitylab" / "nativev4"


class RealtimePipelineContractTests(unittest.TestCase):
    def test_worker_has_independent_fast_latest_lane(self) -> None:
        source = (SERVER / "realtime_worker.py").read_text(encoding="utf-8")
        self.assertIn("realtime_lottery_client.fetch_latest", source)
        self.assertIn("_FAST_WINDOW_BEFORE_MS = 60_000", source)
        self.assertIn("wait = min(wait, 2.0)", source)
        self.assertLess(
            source.index("database.save_draws([latest])"),
            source.index("database.settle_forecasts(lottery_key)"),
        )
        self.assertIn("_NOTIFY_EXECUTOR.submit(_after_draw_notifications", source)
        self.assertIn('"realtime_worker_heartbeat"', source)
        self.assertIn('"detection_delay_ms"', source)

    def test_deploy_runs_realtime_worker(self) -> None:
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn('command: ["python", "-m", "app.realtime_worker"]', compose)
        self.assertIn("realtime-split-lane", compose)

    def test_push_runtime_monkey_patch_stack_is_retired(self) -> None:
        runtime = (SERVER / "runtime_optimizations.py").read_text(encoding="utf-8")
        delivery = (SERVER / "push_delivery_v3.py").read_text(encoding="utf-8")
        push = (SERVER / "push_alerts.py").read_text(encoding="utf-8")
        self.assertNotIn("install_push_runtime_v2()", runtime)
        self.assertNotIn("install_push_runtime_fixes()", runtime)
        self.assertNotIn("push_alerts_module._send_fcm =", delivery)
        self.assertIn("_DELIVERY_BATCH_EXECUTOR", push)
        self.assertIn("_DELIVERY_CHANNEL_EXECUTOR", push)
        self.assertIn("# Data-only is intentional", push)
        self.assertIn("timeout=6", push)

    def test_app_refreshes_latest_first_and_matches_server_period_semantics(self) -> None:
        lottery = (APP / "data" / "LotteryApi.kt").read_text(encoding="utf-8")
        self.assertIn("verifiedHistoryCache", lottery)
        self.assertIn('firstText(value, "nextIssue", "drawIssue")', lottery)
        self.assertLess(
            lottery.index("fetchLatestWithRetry(lottery, requestToken)"),
            lottery.index("fetchDates(lottery, dates, requestToken)"),
        )
        self.assertIn("normalizeNextPeriod", lottery)
        self.assertIn("connectTimeout = 4_000", lottery)

    def test_push_and_foreground_both_trigger_fast_app_refresh(self) -> None:
        coordinator = (APP / "push" / "PushAlertCoordinator.kt").read_text(encoding="utf-8")
        runtime = (APP / "TianjiRuntime.kt").read_text(encoding="utf-8")
        ui = (APP / "ui" / "TianjiApp.kt").read_text(encoding="utf-8")
        self.assertIn("setRealtimeRefreshCallback", coordinator)
        self.assertIn("requestRealtimeRefresh()", coordinator)
        self.assertIn("appController.refresh()", runtime)
        self.assertIn("remaining in -90_000L..60_000L -> 3_000L", ui)
        self.assertIn("remaining in 60_001L..180_000L -> 8_000L", ui)

    def test_console_has_adaptive_lightweight_draw_refresh(self) -> None:
        console = (SERVER / "console_v3.py").read_text(encoding="utf-8")
        self.assertIn("refreshRealtimeDraws", console)
        self.assertIn("remaining>=-90000&&remaining<=60000", console)
        self.assertIn("delay=Math.min(delay,3000)", console)
        self.assertIn("delay=Math.min(delay,8000)", console)


if __name__ == "__main__":
    unittest.main()
