"""AppConfig for django-query-optimizer."""

from __future__ import annotations

from django.apps import AppConfig


class DjangoQueryOptimizerConfig(AppConfig):
    """Application configuration for django-query-optimizer."""

    name = "django_query_optimizer"
    verbose_name = "Django Query Optimizer"
    default_auto_field = "django.db.models.AutoField"
