from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from . import push_alerts, push_runtime_v2


_INSTALLED = False


class _SettingsOverlay:
    def __init__(self, active: Any, fallback: Any) -> None:
        self.active = active
        self.fallback = fallback

    def __getattr__(self, name: str) -> Any:
        if hasattr(self.active, name):
            return getattr(self.active, name)
        return getattr(self.fallback, name)


def _dynamic_settings(call: Callable[..., Any]) -> Callable[..., Any]:
    """Resolve replaced settings at call time while retaining v2 defaults."""

    @wraps(call)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        previous = push_runtime_v2.settings
        push_runtime_v2.settings = _SettingsOverlay(push_alerts.settings, previous)
        try:
            return call(*args, **kwargs)
        finally:
            push_runtime_v2.settings = previous

    return wrapped


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    push_alerts.deliver_pending_alerts = _dynamic_settings(
        push_alerts.deliver_pending_alerts
    )
    push_alerts.process_prediction_alerts = _dynamic_settings(
        push_alerts.process_prediction_alerts
    )
    _INSTALLED = True
