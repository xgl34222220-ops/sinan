"""Tianji cloud backend."""

from .runtime_patches import install as _install_runtime_patches

_install_runtime_patches()
del _install_runtime_patches

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
