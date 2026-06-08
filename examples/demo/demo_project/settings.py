"""Minimal Django settings for the django-query-optimizer demo project.

Development-only configuration. It wires the optimizer in three ways:

1. ``django_query_optimizer.install()`` activates the ORM execute-wrapper hook.
2. ``QueryOptimizerMiddleware`` records every HTTP request into the in-process
   ``QueryStore`` (read by the admin dashboard).
3. ``django_query_optimizer`` is added to ``INSTALLED_APPS`` so the
   "Query Optimizer" admin dashboard appears.

Never use these settings in production — both the install hook and the
middleware add per-query overhead.
"""

from __future__ import annotations

from pathlib import Path

import django_query_optimizer

BASE_DIR = Path(__file__).resolve().parent.parent

# Dev-only dummy secret. Do not reuse outside this demo.
SECRET_KEY = "demo-insecure-key-not-for-production"  # noqa: S105
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # The optimizer app — exposes the "Query Optimizer" admin dashboard.
    "django_query_optimizer",
    # Demo app with intentionally N+1-prone models.
    "catalog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Must come AFTER SessionMiddleware. Records queries per request.
    "django_query_optimizer.middleware.query_collector_middleware.QueryOptimizerMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "demo_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = None

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Activate the ORM query-recording hook (idempotent).
django_query_optimizer.install()
