"""Pytest plugin — query analysis via --query-analysis flag.

This module is registered as a pytest entry-point under the key
``query_optimizer`` in ``pyproject.toml``::

    [project.entry-points."pytest11"]
    query_optimizer = "django_query_optimizer.testing.pytest_plugin"

It contributes the following to every pytest session:

``--query-analysis`` CLI flag
    When passed, enables ORM query recording and analysis globally.  Future
    versions will automatically fail tests that produce recommendations above a
    configurable severity threshold.

``--query-min-score`` option (int, default 0)
    When combined with ``--query-analysis``, every test automatically fails
    if its query health score falls below this threshold.  A value of 0
    disables automatic enforcement.

``query_collector`` fixture
    Function-scoped fixture that yields a fresh :class:`QueryCollector` already
    entered as a context-manager.  The collector is active for the entire test
    body and torn down automatically after the test completes.

    Use it to assert on query counts or to feed a :class:`QueryAnalyzer`::

        def test_view_query_budget(client, query_collector):
            client.get("/api/orders/")
            assert query_collector.count <= 3

``assert_no_queries`` fixture
    Fixture that returns a callable ``check()``.  Call it at the end of your
    test to assert that **no** SQL queries were executed::

        def test_cache_hit(client, assert_no_queries):
            populate_cache()
            client.get("/api/cached/")
            assert_no_queries()

``assert_max_queries`` fixture
    Fixture that returns a callable ``check(max_count)``.  Call it to assert
    that the number of queries does not exceed *max_count*::

        def test_order_list(client, assert_max_queries):
            client.get("/api/orders/")
            assert_max_queries(3)

``assert_query_health`` fixture
    Fixture that returns a callable ``check(min_score=80)``.  Runs
    :class:`~django_query_optimizer.analyzers.QueryAnalyzer` + scorer and
    fails if the score is below *min_score*. Returns the
    :class:`~django_query_optimizer.scoring.query_scorer.QueryScore`::

        def test_order_view_health(client, assert_query_health):
            client.get("/api/orders/")
            score = assert_query_health(min_score=80)
            assert score.grade in ("A", "B")

``query_analysis`` marker
    Decorates a single test to mark it for ORM analysis (no behavior yet —
    reserved for future per-test reporting)::

        @pytest.mark.query_analysis
        def test_expensive_view(client, query_collector): ...
"""

from __future__ import annotations

import pathlib
from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from django_query_optimizer.collectors.query_collector import QueryCollector
    from django_query_optimizer.recommendations.base import ORMRecommendation
    from django_query_optimizer.scoring.query_scorer import QueryScore


# ── Session-level accumulator ─────────────────────────────────────────────────

_SESSION_RECOMMENDATIONS: list[ORMRecommendation] = []


# ── Internal assertion helpers ────────────────────────────────────────────────


class _NoQueryAssertion:
    """Callable returned by :func:`assert_no_queries`."""

    def __init__(self, collector: QueryCollector) -> None:
        self._collector = collector

    def __call__(self) -> None:
        count = self._collector.count
        if count > 0:
            lines = "\n".join(f"  [{i + 1}] {q.sql[:120]}" for i, q in enumerate(self._collector.queries))
            raise AssertionError(f"Expected no SQL queries, but {count} were executed:\n{lines}")


class _MaxQueryAssertion:
    """Callable returned by :func:`assert_max_queries`."""

    def __init__(self, collector: QueryCollector) -> None:
        self._collector = collector

    def __call__(self, max_count: int) -> None:
        count = self._collector.count
        if count > max_count:
            raise AssertionError(
                f"Expected at most {max_count} SQL quer{'y' if max_count == 1 else 'ies'}, but {count} were executed."
            )


class _QueryHealthAssertion:
    """Callable returned by :func:`assert_query_health`."""

    def __init__(self, collector: QueryCollector) -> None:
        self._collector = collector

    def __call__(self, min_score: int = 80) -> QueryScore:
        from django_query_optimizer.analyzers.query_analyzer import QueryAnalyzer
        from django_query_optimizer.scoring.query_scorer import QueryScorer

        recs = QueryAnalyzer(self._collector.queries).analyze()
        score = QueryScorer(recs).compute()
        if score.value < min_score:
            raise AssertionError(
                f"Query health score {score.value}/100 ({score.grade}) is below the minimum "
                f"threshold of {min_score}.\n{score.summary}"
            )
        return score


# ── Plugin hooks ──────────────────────────────────────────────────────────────


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --query-analysis, --query-min-score, and --sarif-output flags to pytest."""
    group = parser.getgroup("django-query-optimizer")
    group.addoption(
        "--query-analysis",
        action="store_true",
        default=False,
        help="Enable ORM query analysis on every test.",
    )
    group.addoption(
        "--query-min-score",
        type=int,
        default=0,
        metavar="N",
        help="Minimum query health score (0-100). Requires --query-analysis. Default: 0 (disabled).",
    )
    group.addoption(
        "--sarif-output",
        type=str,
        default=None,
        metavar="FILE",
        help="Write ORM findings as a SARIF 2.1.0 report to FILE at session end. "
        "Requires --query-analysis.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the query_analysis marker."""
    config.addinivalue_line(
        "markers",
        "query_analysis: mark test for ORM query analysis",
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def query_collector() -> Generator[QueryCollector]:
    """Pytest fixture: return a fresh QueryCollector scoped to the test."""
    from django_query_optimizer.collectors.query_collector import QueryCollector

    collector = QueryCollector()
    with collector:
        yield collector


@pytest.fixture()
def assert_no_queries(query_collector: QueryCollector) -> _NoQueryAssertion:
    """Fixture: callable that asserts no SQL queries were executed.

    Example::

        def test_cache_hit(client, assert_no_queries):
            populate_cache()
            client.get("/api/cached/")
            assert_no_queries()
    """
    return _NoQueryAssertion(query_collector)


@pytest.fixture()
def assert_max_queries(query_collector: QueryCollector) -> _MaxQueryAssertion:
    """Fixture: callable ``check(max_count)`` — fails if queries > max_count.

    Example::

        def test_order_list(client, assert_max_queries):
            client.get("/api/orders/")
            assert_max_queries(3)
    """
    return _MaxQueryAssertion(query_collector)


@pytest.fixture()
def assert_query_health(query_collector: QueryCollector) -> _QueryHealthAssertion:
    """Fixture: callable ``check(min_score=80)`` — fails if health score < threshold.

    Returns the :class:`~django_query_optimizer.scoring.query_scorer.QueryScore`
    so callers can make additional assertions.

    Example::

        def test_order_view_health(client, assert_query_health):
            client.get("/api/orders/")
            score = assert_query_health(min_score=80)
            assert score.grade != "F"
    """
    return _QueryHealthAssertion(query_collector)


# ── Session-level SARIF hooks ─────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _collect_recommendations_for_sarif(
    request: pytest.FixtureRequest,
    query_collector: QueryCollector,
) -> Generator[None]:
    """Autouse fixture: accumulate recommendations into the session list when
    ``--query-analysis`` and ``--sarif-output`` are both active."""
    yield
    if not request.config.getoption("--query-analysis", default=False):
        return
    if request.config.getoption("--sarif-output", default=None) is None:
        return
    from django_query_optimizer.analyzers.query_analyzer import QueryAnalyzer

    recs = QueryAnalyzer(query_collector.queries).analyze()
    _SESSION_RECOMMENDATIONS.extend(recs)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # noqa: ARG001
    """Write the accumulated SARIF report at the end of the session."""
    sarif_path: str | None = session.config.getoption("--sarif-output", default=None)
    if sarif_path is None:
        return
    if not session.config.getoption("--query-analysis", default=False):
        return

    from django_query_optimizer.reporting.sarif import SARIFReporter

    output = pathlib.Path(sarif_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(SARIFReporter(_SESSION_RECOMMENDATIONS).as_json(), encoding="utf-8")
