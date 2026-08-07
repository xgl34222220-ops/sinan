from __future__ import annotations

from .db import Database, database
from . import fixed_target_runtime_guard


_INSTALLED = False


def install() -> None:
    """Make fixed-235780 settlement survive later instance-level runtime hooks."""
    global _INSTALLED
    if _INSTALLED:
        return

    original_class_settle = Database.settle_forecasts

    def settle_fixed235780(self: Database, lottery: str) -> int:
        fixed_target_runtime_guard._normalize_fixed_mode_rows(lottery)
        result = original_class_settle(self, lottery)
        fixed_target_runtime_guard._normalize_fixed_mode_rows(lottery)
        return result

    setattr(settle_fixed235780, "_tianji_fixed235780_guard", True)
    Database.settle_forecasts = settle_fixed235780

    # runtime_optimizations historically installs an instance MethodType. Remove any
    # instance shadow so all callers resolve through the guarded class method above.
    database.__dict__.pop("settle_forecasts", None)
    _INSTALLED = True
