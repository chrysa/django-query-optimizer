"""Pytest plugin — query analysis via --query-analysis flag.

This module is registered as a pytest entry-point under the key
``query_optimizer`` in ``pyproject.toml``::

    [project.entry-points."pytest11"]
    query_optimizer = "django_query_optimizer.testing.pytest_plugin"

It contributes two things to every pytest session:

``--query-analysis`` CLI flag
    When passed, enables ORM query recording and analysis globally.  Future
    versions will automatically fail tests that produce recommendations above a
    configurable severity threshold.

``query_collector`` fixture
    Function-scoped fixture that yields a fresh :class:`QueryCollector` already
    entered as a context-manager.  The collector is active for the entire test
    body and torn down automatically after the test completes.

    Use it to assert on query counts or to feed a :class:`QueryAnalyzer`::

        def test_view_query_budget(client, query_collector):
            client.get("/api/orders/")
            assert query_collector.count <= 3

        def test_no_slow_queries(client, query_collector):
            from django_query_optimizer import QueryAnalyzer
            from django_query_optimizer.recommendations.base import Severity

            client.get("/api/orders/")
            recs = QueryAnalyzer(query_collector.queries).analyze()
            assert not any(r.severity == Severity.HIGH for r in recs)

``query_analysis`` marker
    Decorates a single test to mark it for ORM analysis (no behavior yet —
    reserved for Phase 3 per-test reporting)::

        @pytest.mark.query_analysis
        def test_expensive_view(client, query_collector): ...
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from django_query_optimizer.collectors.query_collector import QueryCollector


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --query-analysis flag to pytest."""
    group = parser.getgroup("django-query-optimizer")
    group.addoption(
        "--query-analysis",
        action="store_true",
        default=False,
        help="Enable ORM query analysis on every test.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the query_analysis marker."""
    config.addinivalue_line(
        "markers",
        "query_analysis: mark test for ORM query analysis",
    )


@pytest.fixture()
def query_collector() -> Generator[QueryCollector]:
    """Pytest fixture: return a fresh QueryCollector scoped to the test."""
    from django_query_optimizer.collectors.query_collector import QueryCollector

    collector = QueryCollector()
    with collector:
        yield collector
