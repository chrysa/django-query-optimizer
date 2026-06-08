#!/usr/bin/env python
"""Django management entry point for the django-query-optimizer demo project."""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Run administrative tasks against the demo project settings."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - import guard
        raise ImportError(
            "Couldn't import Django. Install it with `pip install -e \".[dev]\"` "
            "from the repository root, then run this command again."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
