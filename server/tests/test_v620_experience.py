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
        self.assertIn("API 出结果 → 天机发现", source)
        self.assertIn("单次探测请求", source)
        self.assertIn("写库 + 结算", source)
        self.assertIn("/admin/api/realtime", source)

    def test_app_realtime_refresh_no_longer_uses_java_reflection(self) -> None:
        controller = (
            ROOT
            / "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt"
        ).read_text(encoding="utf-8")
        bridge = (
            ROOT
            / "app/src/main/java/com/tianji/probabilitylab/nativev4/AppRealtimeRefresh.kt"
        ).read_text(encoding="utf-8")
        self.assertIn("internal fun refreshCurrentLottery()", controller)
        self.assertNotIn("java.lang.reflect", bridge)
        self.assertNotIn("getDeclaredMethod", bridge)

    def test_v62_home_and_adaptive_navigation_are_wired(self) -> None:
        app_source = (
            ROOT
            / "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt"
        ).read_text(encoding="utf-8")
        build_source = (ROOT / "app/build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn("V62ForecastScreen", app_source)
        self.assertIn("V62AdaptiveScaffold", app_source)
        self.assertIn("material3.adaptive:adaptive:1.2.0", build_source)
        self.assertIn("com.android.compose.screenshot", build_source)


if __name__ == "__main__":
    unittest.main()
