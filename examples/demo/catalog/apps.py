"""AppConfig for the demo catalog app."""

from __future__ import annotations

from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """Configuration for the demo catalog app."""

    default_auto_field = "django.db.models.AutoField"
    name = "catalog"
