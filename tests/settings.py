"""Minimal Django settings for the test suite."""

from __future__ import annotations

SECRET_KEY = "django-query-optimizer-test-secret-key-not-for-production"  # noqa: S105

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
