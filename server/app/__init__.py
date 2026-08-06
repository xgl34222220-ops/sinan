"""Tianji cloud backend."""

from .runtime_patches import install as _install_runtime_patches

_install_runtime_patches()
del _install_runtime_patches
