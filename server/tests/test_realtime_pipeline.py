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

    def test_push_and_foreground_keep_both_lotteries_current(self) -> None:
        coordinator = (APP / "push" / "PushAlertCoordinator.kt").read_text(encoding="utf-8")
        runtime = (APP / "TianjiRuntime.kt").read_text(encoding="utf-8")
        controller = (APP / "AppController.kt").read_text(encoding="utf-8")
        ui = (APP / "ui" / "TianjiApp.kt").read_text(encoding="utf-8")
        realtime_client = (APP / "data" / "CloudRealtimeOverviewApi.kt").read_text(encoding="utf-8")
        realtime_public = (SERVER / "realtime_public.py").read_text(encoding="utf-8")

        self.assertIn("setRealtimeRefreshCallback", coordinator)
        self.assertIn("requestRealtimeRefresh()", coordinator)
        self.assertIn("appController.refresh()", runtime)
        self.assertIn("fun refresh()", controller)
        self.assertIn("refreshAll(force = true)", controller)
        self.assertFalse((APP / "AppRealtimeRefresh.kt").exists())

        # Foreground polling uses one light server response for both lotteries, then only enters
        # the heavy all-lottery lane on an actual period change or a bounded fallback interval.
        self.assertIn("CloudRealtimeOverviewApi", ui)
        self.assertIn("realtimeApi.fetchOverview()", ui)
        self.assertIn("controller.refresh()", ui)
        self.assertNotIn("controller.refreshCurrentLottery()", ui)
        self.assertIn("nearestDrawMs in -90_000L..60_000L -> 2_500L", ui)
        self.assertIn("nearestDrawMs in 60_001L..180_000L -> 6_000L", ui)
        self.assertIn('URL("$baseUrl/v1/public/realtime")', realtime_client)
        self.assertIn('@app.get("/v1/public/realtime"', realtime_public)

    def test_console_has_adaptive_lightweight_draw_refresh(self) -> None:
        console = (SERVER / "console_v3.py").read_text(encoding="utf-8")
        self.assertIn("refreshRealtimeDraws", console)
        self.assertIn("remaining>=-90000&&remaining<=60000", console)
        self.assertIn("delay=Math.min(delay,3000)", console)
        self.assertIn("delay=Math.min(delay,8000)", console)


if __name__ == "__main__":
    unittest.main()
