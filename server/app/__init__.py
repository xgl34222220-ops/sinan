"""Tianji cloud backend."""

from . import ai as _ai
from .runtime_patches import (
    _ORIGINAL_AI_ANALYZE as _base_ai_analyze,
    install as _install_runtime_patches,
)

_install_runtime_patches()
# Keep the useful admin/streak runtime fixes, but retire the old cross-source
# "independence" rule.  Agreement with the native model is evidence, not an
# error condition: AI must never be forced to change or discard a prediction
# just because the two independently derived Top6 sets overlap.
_ai.analyze = _base_ai_analyze
del _ai, _base_ai_analyze, _install_runtime_patches

# Dynamic AI v2: keep the original multi-reviewer ensemble and layer settled
# walk-forward learning on top.  The old fixed-235780 bridges intentionally are
# not installed here: AI Top6/Top7 must be derived from the current probability
# ranking and historical AI forecasts must never be rewritten during startup.
from .ai_continual_bridge import install as _install_ai_continual_bridge

_install_ai_continual_bridge()
del _install_ai_continual_bridge

from .realtime_admin import install as _install_realtime_admin

_install_realtime_admin()
del _install_realtime_admin

from .console_final_polish import install as _install_console_final_polish

_install_console_final_polish()
del _install_console_final_polish
