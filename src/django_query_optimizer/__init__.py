"""
django-query-optimizer — Intelligent ORM analysis and optimization for Django.

Public API surface:
    QueryCollector          — collects SQL queries at runtime
    QueryAnalyzer           — analyzes collected queries for issues
    ORMRecommendation       — a single optimization recommendation
    install                 — activate the optimizer middleware in Django settings
"""

from __future__ import annotations

from django_query_optimizer._internal.version import __version__
from django_query_optimizer.analyzers.query_analyzer import QueryAnalyzer
from django_query_optimizer.collectors.query_collector import QueryCollector
from django_query_optimizer.recommendations.base import ORMRecommendation

__all__ = [
    "__version__",
    "QueryCollector",
    "QueryAnalyzer",
    "ORMRecommendation",
    "install",
]


def install() -> None:
    """Register django-query-optimizer middleware and signal handlers.

    Call this inside your Django ``AppConfig.ready()`` or at the bottom of
    ``settings.py`` during development.  Safe to call multiple times
    (idempotent).

    Example::

        # settings.py
        import django_query_optimizer
        django_query_optimizer.install()
    """
    from django_query_optimizer._internal.bootstrap import bootstrap

    bootstrap()
