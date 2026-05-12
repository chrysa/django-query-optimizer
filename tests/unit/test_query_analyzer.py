"""Unit tests for QueryAnalyzer."""

from __future__ import annotations

import pytest

from django_query_optimizer.analyzers.query_analyzer import (
    DUPLICATE_MIN_COUNT,
    SLOW_QUERY_THRESHOLD_MS,
    QueryAnalyzer,
)
from django_query_optimizer.collectors.query_collector import CapturedQuery
from django_query_optimizer.recommendations.base import Severity


def _make_query(sql: str = "SELECT 1", duration_ms: float = 1.0) -> CapturedQuery:
    return CapturedQuery(sql=sql, duration_ms=duration_ms, stack_trace=[])


class TestQueryAnalyzerSlowQueries:
    def test_no_recommendations_for_fast_queries(self) -> None:
        queries = [_make_query(duration_ms=SLOW_QUERY_THRESHOLD_MS - 1)]
        analyzer = QueryAnalyzer(queries)
        recs = analyzer.analyze()
        assert not any(r.issue_type == "slow_query" for r in recs)

    def test_detects_slow_query_at_threshold(self) -> None:
        queries = [_make_query(duration_ms=SLOW_QUERY_THRESHOLD_MS)]
        analyzer = QueryAnalyzer(queries)
        recs = analyzer.analyze()
        slow = [r for r in recs if r.issue_type == "slow_query"]
        assert len(slow) == 1
        assert slow[0].severity == Severity.HIGH

    def test_detects_multiple_slow_queries(self) -> None:
        queries = [
            _make_query("SELECT 1", SLOW_QUERY_THRESHOLD_MS + 10),
            _make_query("SELECT 2", SLOW_QUERY_THRESHOLD_MS + 20),
        ]
        analyzer = QueryAnalyzer(queries)
        slow = [r for r in analyzer.analyze() if r.issue_type == "slow_query"]
        assert len(slow) == 2

    @pytest.mark.parametrize("duration_ms", [0.0, 50.0, 99.9])
    def test_no_slow_query_below_threshold(self, duration_ms: float) -> None:
        analyzer = QueryAnalyzer([_make_query(duration_ms=duration_ms)])
        assert not any(r.issue_type == "slow_query" for r in analyzer.analyze())


class TestQueryAnalyzerDuplicates:
    def test_no_recommendation_for_unique_queries(self) -> None:
        queries = [_make_query("SELECT 1"), _make_query("SELECT 2")]
        analyzer = QueryAnalyzer(queries)
        assert not any(r.issue_type == "duplicate_query" for r in analyzer.analyze())

    def test_detects_duplicate(self) -> None:
        queries = [_make_query("SELECT 1")] * DUPLICATE_MIN_COUNT
        analyzer = QueryAnalyzer(queries)
        dups = [r for r in analyzer.analyze() if r.issue_type == "duplicate_query"]
        assert len(dups) == 1
        assert dups[0].severity == Severity.MEDIUM

    def test_duplicate_count_in_message(self) -> None:
        count = 5
        queries = [_make_query("SELECT 1")] * count
        analyzer = QueryAnalyzer(queries)
        dups = [r for r in analyzer.analyze() if r.issue_type == "duplicate_query"]
        assert str(count) in dups[0].message


class TestQueryAnalyzerSorting:
    def test_recommendations_sorted_by_severity(self) -> None:
        queries = [
            _make_query("SELECT 1", SLOW_QUERY_THRESHOLD_MS + 10),  # HIGH
            _make_query("SELECT 2"),
            _make_query("SELECT 2"),  # MEDIUM duplicate
        ]
        analyzer = QueryAnalyzer(queries)
        recs = analyzer.analyze()
        severities = [r.severity for r in recs]
        assert severities == sorted(
            severities,
            key=lambda s: ["critical", "high", "medium", "low", "info"].index(s.value),
        )
