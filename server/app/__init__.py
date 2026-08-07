"""Tianji cloud backend."""

from .runtime_patches import install as _install_runtime_patches

_install_runtime_patches()
del _install_runtime_patches

from .ai_continual_bridge import install as _install_ai_continual_bridge

_install_ai_continual_bridge()
del _install_ai_continual_bridge

from .fixed_target_bridge import install as _install_fixed_target_bridge

_install_fixed_target_bridge()
del _install_fixed_target_bridge
