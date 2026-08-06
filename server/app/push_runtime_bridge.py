from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from . import push_alerts, push_runtime_v2


_INSTALLED = False


def _dynamic_settings(call: Callable[..., Any]) -> Callable[..., Any]:
    """Keep v2 runtime aligned with the active push settings object.

    Production uses the same immutable Settings instance. Tests and future runtime
    reloads may replace ``push_alerts.settings``; the bridge deliberately resolves
    that object at call time instead of retaining a stale import reference.
    """

    @wraps(call)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        previous = push_runtime_v2.settings
        push_runtime_v2.settings = push_alerts.settings
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
