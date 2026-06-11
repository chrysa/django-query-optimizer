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

from ._internal.version import __version__
from .analyzers.query_analyzer import QueryAnalyzer
from .collectors.query_collector import QueryCollector
from .detectors.drf_serializer import DRFSerializerDetector
from .detectors.n_plus_one import NplusOneDetector
from .detectors.select_related import SelectRelatedDetector
from .middleware.query_collector_middleware import QueryOptimizerMiddleware
from .recommendations.base import ORMRecommendation, Severity
from .regression.detector import RegressionDetector, RegressionResult
from .reporting.sarif import SARIFReporter
from .scoring.query_scorer import QueryScore, QueryScorer
from .store import QueryStore, RequestRecord

__all__ = [
    "__version__",
    "DRFSerializerDetector",
    "NplusOneDetector",
    "ORMRecommendation",
    "QueryAnalyzer",
    "QueryCollector",
    "QueryOptimizerMiddleware",
    "QueryScore",
    "QueryScorer",
    "QueryStore",
    "RegressionDetector",
    "RegressionResult",
    "RequestRecord",
    "SARIFReporter",
    "SelectRelatedDetector",
    "Severity",
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
