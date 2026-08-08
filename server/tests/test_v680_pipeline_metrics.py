from __future__ import annotations


def test_percentile_interpolates_recent_window():
    from app import realtime_worker

    values = [100, 200, 300, 400, 500]
    assert realtime_worker._percentile(values, 0.50) == 300
    assert realtime_worker._percentile(values, 0.95) == 480


def test_rolling_keeps_only_last_100_samples():
    from app import realtime_worker

    previous = {"samples": list(range(100))}
    values = realtime_worker._rolling(previous, "samples", 100)
    assert len(values) == 100
    assert values[0] == 1
    assert values[-1] == 100


def test_rolling_ignores_missing_metric():
    from app import realtime_worker

    previous = {"samples": [10, 20]}
    assert realtime_worker._rolling(previous, "samples", None) == [10, 20]
