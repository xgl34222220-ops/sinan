from __future__ import annotations

import json
from types import SimpleNamespace

from app import realtime_public


def test_public_realtime_payload_contains_both_lotteries(monkeypatch):
    periods = {
        "xyft": ("101", list(range(1, 11))),
        "azxy10": ("201", list(range(10, 0, -1))),
    }

    def latest_draw(key: str):
        period, numbers = periods[key]
        return SimpleNamespace(period=period, numbers=numbers)

    def get_state(key: str):
        lottery = key.split(":", 1)[1]
        next_period = "102" if lottery == "xyft" else "202"
        payload = {
            "next_period": next_period,
            "next_draw_at_epoch_ms": 20_000 if lottery == "xyft" else 30_000,
            "completed_at_epoch_ms": 15_000 if lottery == "xyft" else 16_000,
        }
        return json.dumps(payload), 17_000

    monkeypatch.setattr(realtime_public.database, "latest_draw", latest_draw)
    monkeypatch.setattr(realtime_public.database, "get_state", get_state)

    payload = realtime_public.public_realtime_payload(now_ms=18_000)

    assert payload["generated_at_epoch_ms"] == 18_000
    rows = {row["key"]: row for row in payload["lotteries"]}
    assert set(rows) == {"xyft", "azxy10"}
    assert rows["xyft"]["latest_period"] == "101"
    assert rows["xyft"]["next_period"] == "102"
    assert rows["azxy10"]["numbers"] == list(range(10, 0, -1))
    assert rows["azxy10"]["synced_at_epoch_ms"] == 16_000


def test_public_realtime_route_is_installed():
    from app.main import app

    assert any(getattr(route, "path", None) == "/v1/public/realtime" for route in app.routes)
