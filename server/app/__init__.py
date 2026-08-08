"""Tianji cloud backend."""

from .runtime_patches import install as _install_runtime_patches

# Reporting/streak fixes only. No runtime rule is allowed to force AI away from
# the native prediction or mutate an already frozen forecast.
_install_runtime_patches()
del _install_runtime_patches

# Dynamic AI v2: the original anonymous multi-reviewer engine stays responsible
# for dynamic position/number judgement, while settled walk-forward learning
# calibrates both the position choice and the final number probabilities.
# Legacy fixed-235780 bridges/guards intentionally are not installed.
from .ai_continual_bridge import install as _install_ai_continual_bridge

_install_ai_continual_bridge()
del _install_ai_continual_bridge

from .realtime_admin import install as _install_realtime_admin

_install_realtime_admin()
del _install_realtime_admin

from .realtime_public import install as _install_realtime_public

_install_realtime_public()
del _install_realtime_public

from .console_final_polish import install as _install_console_final_polish

_install_console_final_polish()
del _install_console_final_polish
