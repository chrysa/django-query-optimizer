"""Pytest plugin — query analysis via --query-analysis flag."""

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
