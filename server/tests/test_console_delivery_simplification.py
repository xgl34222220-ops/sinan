from pathlib import Path


def test_console_hides_internal_stage_and_miss_watch_workspaces():
    root = Path(__file__).resolve().parents[1] / "app"
    js = (root / "console_v594.js").read_text(encoding="utf-8")
    py = (root / "console_v3.py").read_text(encoding="utf-8")
    assert "v597MissWatchWorkspace" not in js
    assert "双彩种三期不中预警" not in js
    assert "loadRecords();loadInsights();loadDraws();setInterval(loadDraws,30000);" in js
    assert "<h3>服务状态</h3>" in py
    assert "stage.name" not in py
    assert "内部任务名、数据库细节与毫秒耗时已隐藏" in py
    assert ".closest(\'.card\')?.remove()" not in js
    assert "legacyDiagnosticsCard.setAttribute(\'hidden\',\'hidden\')" in js
    assert "legacyDiagnosticsCard.setAttribute(\'aria-hidden\',\'true\')" in js


def test_telegram_latency_policy_is_explicit():
    root = Path(__file__).resolve().parents[1] / "app"
    events = (root / "telegram_events.py").read_text(encoding="utf-8")
    alerts = (root / "telegram_alerts.py").read_text(encoding="utf-8")
    service = (root / "service.py").read_text(encoding="utf-8")
    assert "_MAX_PREDICTION_EVENT_AGE_MS = 8 * 60_000" in events
    assert "_RETRY_COOLDOWN_MS = 60_000" in events
    assert "timeout_seconds: int = 6" in alerts
    assert service.index('stages, "deliver_push"') < service.index('stages, "deliver_telegram"')
