"""Shared test fixtures."""

from __future__ import annotations

import django
import pytest


@pytest.fixture(autouse=True)
def _django_setup() -> None:
    """Ensure Django is set up before any test."""
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    django.setup()
