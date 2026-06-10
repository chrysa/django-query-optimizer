"""Internal version accessor — reads installed package metadata.

Single source of truth is ``pyproject.toml [project].version``. Centralised
here so modules that need the version (e.g. SARIF report headers) import it
without importing the package root and creating an import cycle.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("django-query-optimizer")
except PackageNotFoundError:  # editable install / not installed
    __version__ = "0.0.0+unknown"
