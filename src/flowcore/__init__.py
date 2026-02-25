"""Compatibility package for legacy ``flowcore`` imports.

This project was migrated to the ``lee`` package namespace, but some
environments still execute old console scripts that import
``flowcore.cli.main``. Keeping this shim avoids startup failures for those
stale entrypoints.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lee-framework")
except PackageNotFoundError:  # pragma: no cover - fallback for source-only usage
    __version__ = "0.1.0"

__all__ = ["__version__"]
