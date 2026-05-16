"""Query analyzer — detects ORM issues in a list of CapturedQuery objects.

This module contains ``QueryAnalyzer``, the main entry point for inspecting a
collected set of queries.  It iterates over a configurable pipeline of
detectors and aggregates their ``ORMRecommendation`` results.

Threshold constants
-------------------
``SLOW_QUERY_THRESHOLD_MS``
    Queries that take longer than this value (in milliseconds) are flagged as
    HIGH severity.  Default: **100.0 ms**.

``DUPLICATE_MIN_COUNT``
    A SQL statement that appears at least this many times in the collected
    queries is flagged as a duplicate.  Default: **2**.

Both constants are module-level and can be monkey-patched in tests or
configuration code::

    import django_query_optimizer.analyzers.query_analyzer as _qa
    _qa.SLOW_QUERY_THRESHOLD_MS = 50.0
    _qa.DUPLICATE_MIN_COUNT = 3

Example::

    from django_query_optimizer.analyzers.query_analyzer import QueryAnalyzer
    from django_query_optimizer.collectors.query_collector import QueryCollector

    with QueryCollector() as col:
        list(MyModel.objects.all())

    for rec in QueryAnalyzer(col.queries).analyze():
        print(rec.severity, rec.message)
"""

from __future__ import annotations

from collections import Counter

from django_query_optimizer.collectors.query_collector import CapturedQuery
from django_query_optimizer.detectors.n_plus_one import NplusOneDetector
from django_query_optimizer.detectors.select_related import SelectRelatedDetector
from django_query_optimizer.recommendations.base import ORMRecommendation, Severity
from django_query_optimizer.scoring.query_scorer import QueryScore, QueryScorer

# Threshold constants
SLOW_QUERY_THRESHOLD_MS: float = 100.0
DUPLICATE_MIN_COUNT: int = 2


class QueryAnalyzer:
    """Analyze a list of :class:`~django_query_optimizer.collectors.CapturedQuery`
    objects and produce :class:`~django_query_optimizer.recommendations.ORMRecommendation`
    instances.

    Example::

        with QueryCollector() as collector:
            list(Order.objects.all())
        analyzer = QueryAnalyzer(collector.queries)
        for rec in analyzer.analyze():
            print(rec.severity, rec.message)
    """

    def __init__(self, queries: list[CapturedQuery]) -> None:
        self._queries = queries

    def analyze(self) -> list[ORMRecommendation]:
        """Run all detectors and return sorted recommendations (most severe first)."""
        recommendations: list[ORMRecommendation] = []
        recommendations.extend(self._detect_slow_queries())
        recommendations.extend(self._detect_duplicate_queries())
        recommendations.extend(NplusOneDetector().detect(self._queries))
        recommendations.extend(SelectRelatedDetector().detect(self._queries))
        return sorted(recommendations)

    def score(self) -> QueryScore:
        """Return a health score summarising all detected issues.

        Equivalent to ``QueryScorer(self.analyze()).compute()``.

        Example::

            analyzer = QueryAnalyzer(collector.queries)
            score = analyzer.score()
            print(score.summary)  # "Score 85/100 (B) — 1 issue(s): 1 high"
        """
        return QueryScorer(self.analyze()).compute()

    # ── Detectors ─────────────────────────────────────────────────────────────

    def _detect_slow_queries(self) -> list[ORMRecommendation]:
        """Flag queries that exceed the slow-query threshold."""
        results: list[ORMRecommendation] = []
        for query in self._queries:
            if query.duration_ms >= SLOW_QUERY_THRESHOLD_MS:
                results.append(
                    ORMRecommendation(
                        issue_type="slow_query",
                        severity=Severity.HIGH,
                        message=(f"Query took {query.duration_ms:.1f} ms (threshold: {SLOW_QUERY_THRESHOLD_MS} ms)"),
                        suggestion=(
                            "Consider adding a database index, using only() / values(), or caching the result."
                        ),
                        python_file=query.python_file,
                        python_line=query.python_line,
                    )
                )
        return results

    def _detect_duplicate_queries(self) -> list[ORMRecommendation]:
        """Detect queries whose SQL is executed more than once."""
        results: list[ORMRecommendation] = []
        counts = Counter(q.sql for q in self._queries)
        for sql, count in counts.items():
            if count >= DUPLICATE_MIN_COUNT:
                results.append(
                    ORMRecommendation(
                        issue_type="duplicate_query",
                        severity=Severity.MEDIUM,
                        message=f"Query executed {count} times: {sql[:120]}",
                        suggestion=(
                            "Cache the queryset result, use select_related() / "
                            "prefetch_related(), or restructure the loop."
                        ),
                    )
                )
        return results
