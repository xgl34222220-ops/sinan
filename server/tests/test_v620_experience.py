from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class V620ExperienceContractTests(unittest.TestCase):
    def test_realtime_admin_exposes_detection_and_settlement_latency(self) -> None:
        source = (ROOT / "server/app/realtime_admin.py").read_text(encoding="utf-8")
        for field in (
            "detection_delay_ms",
            "detection_delay_ema_ms",
            "max_detection_delay_ms",
            "probe_latency_ms",
            "settlement_latency_ms",
            "runtime_revision",
        ):
            self.assertIn(field, source)
        self.assertIn('/admin/api/realtime', source)

    def test_console_renders_realtime_latency_cards(self) -> None:
        source = (ROOT / "server/app/console_v3.py").read_text(encoding="utf-8")
        self.assertIn("实时开奖链路", source)
        self.assertIn("开奖发现延迟", source)
        self.assertIn("探测请求", source)
        self.assertIn("写库结算", source)
        self.assertIn("/admin/api/realtime", source)

    def test_console_keeps_compact_health_and_stale_data_states(self) -> None:
        source = (ROOT / "server/app/console_v3.py").read_text(encoding="utf-8")
        self.assertIn("系统健康", source)
        self.assertIn("v630-healthbar", source)
        self.assertIn("latencyLabel", source)
        self.assertIn("数据已过期", source)
        self.assertIn("较 EMA", source)
        self.assertIn("installAfterPanelHead", source)
        self.assertIn("Math.max(...observed)", source)
        self.assertIn("v620-realtime-card ${state}", source)

    def test_app_realtime_refresh_is_a_direct_controller_api(self) -> None:
        controller = (
            ROOT
            / "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt"
        ).read_text(encoding="utf-8")
        bridge = (
            ROOT
            / "app/src/main/java/com/tianji/probabilitylab/nativev4/AppRealtimeRefresh.kt"
        )
        self.assertIn("fun refresh()", controller)
        self.assertIn("refreshAll(force = true)", controller)
        self.assertFalse(bridge.exists())
        self.assertNotIn("java.lang.reflect", controller)
        self.assertNotIn("getDeclaredMethod", controller)

    def test_v67_home_archive_alerts_and_adaptive_navigation_are_wired(self) -> None:
        app_source = (
            ROOT
            / "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt"
        ).read_text(encoding="utf-8")
        forecast_source = (
            ROOT
            / "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/V67ForecastScreen.kt"
        ).read_text(encoding="utf-8")
        build_source = (ROOT / "app/build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn("V67ForecastScreen", app_source)
        self.assertIn("V62ArchiveScreen", app_source)
        self.assertIn("V62PushAlertCenterScreen", app_source)
        self.assertIn("V62AdaptiveScaffold", app_source)
        self.assertIn("V67DualLotteryStrip", forecast_source)
        self.assertIn("AI v2 联合预测", forecast_source)
        self.assertIn("概率对比", forecast_source)
        self.assertIn("material3.adaptive:adaptive:1.2.0", build_source)
        self.assertIn("com.android.compose.screenshot", build_source)

    def test_v63_density_hierarchy_contracts(self) -> None:
        ui_root = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ui"
        forecast = (ui_root / "V62ForecastScreen.kt").read_text(encoding="utf-8")
        archive = (ui_root / "V62ArchiveScreen.kt").read_text(encoding="utf-8")
        alerts = (ui_root / "V62PushAlertCenter.kt").read_text(encoding="utf-8")
        bottom_bar = (ui_root / "MainBottomBar.kt").read_text(encoding="utf-8")
        self.assertNotIn("固定目标 235780", forecast)
        self.assertIn("state.report?.targetPeriod", forecast)
        self.assertIn('stickyHeader("search")', archive)
        self.assertIn("FCM 即时推送正常", alerts)
        self.assertIn("查看预测", alerts)
        self.assertIn("heightIn(min = 62.dp)", bottom_bar)

    def test_v650_mobile_polish_contract(self) -> None:
        source = (ROOT / "server/app/console_v3.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("/* v6.5 UI Final Polish 2: shared density + semantic token layer */"), 1)
        self.assertIn(".topbar .brand h1{display:none}", source)
        self.assertIn(".v620-card-state{min-height:23px;padding:0 8px;font-size:11px}", source)
        self.assertIn(".v620-latency span{font-size:11px", source)
        self.assertIn(".mobile-nav .nav-tail{display:none!important}", source)
        self.assertIn(".tianji-console-v620 .model-choice{min-height:54px", source)
        self.assertIn(".tianji-console-v620 .profile-card{padding:10px", source)
        self.assertIn("background:linear-gradient(145deg,var(--ai),var(--primary2))", source)


if __name__ == "__main__":
    unittest.main()
