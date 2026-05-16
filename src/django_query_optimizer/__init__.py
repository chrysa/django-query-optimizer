"""
django-query-optimizer — Intelligent ORM analysis and optimization for Django.

Public API surface:
    QueryCollector              — collects SQL queries at runtime
    QueryAnalyzer               — analyzes collected queries for issues
    ORMRecommendation           — a single optimization recommendation
    QueryOptimizerMiddleware    — per-request Django middleware
    QueryStore                  — in-memory store for request records
    RequestRecord               — snapshot of one request's query activity
    install                     — activate the optimizer middleware in Django settings
"""

from __future__ import annotations

from django_query_optimizer._internal.version import __version__
from django_query_optimizer.analyzers.query_analyzer import QueryAnalyzer
from django_query_optimizer.collectors.query_collector import QueryCollector
from django_query_optimizer.detectors.n_plus_one import NplusOneDetector
from django_query_optimizer.detectors.select_related import SelectRelatedDetector
from django_query_optimizer.middleware.query_collector_middleware import QueryOptimizerMiddleware
from django_query_optimizer.recommendations.base import ORMRecommendation
from django_query_optimizer.store import QueryStore, RequestRecord

__all__ = [
    "__version__",
    "QueryCollector",
    "QueryAnalyzer",
    "NplusOneDetector",
    "SelectRelatedDetector",
    "ORMRecommendation",
    "QueryOptimizerMiddleware",
    "QueryStore",
    "RequestRecord",
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
