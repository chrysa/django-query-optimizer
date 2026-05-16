"""Unit tests for NplusOneDetector and normalize_sql."""

from __future__ import annotations

import pytest

from django_query_optimizer.collectors.query_collector import CapturedQuery
from django_query_optimizer.detectors.n_plus_one import (
    N_PLUS_ONE_CRITICAL_COUNT,
    N_PLUS_ONE_HIGH_COUNT,
    N_PLUS_ONE_MIN_COUNT,
    NplusOneDetector,
    normalize_sql,
)
from django_query_optimizer.recommendations.base import Severity

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_query(
    sql: str = "SELECT * FROM book WHERE author_id = 1",
    python_file: str = "views.py",
    python_line: int = 42,
    duration_ms: float = 1.0,
) -> CapturedQuery:
    return CapturedQuery(
        sql=sql,
        duration_ms=duration_ms,
        stack_trace=[],
        python_file=python_file,
        python_line=python_line,
    )


def _n_plus_one_queries(
    n: int,
    base_sql: str = "SELECT * FROM book WHERE author_id = {i}",
    python_file: str = "views.py",
    python_line: int = 42,
) -> list[CapturedQuery]:
    return [
        _make_query(
            sql=base_sql.format(i=i),
            python_file=python_file,
            python_line=python_line,
        )
        for i in range(1, n + 1)
    ]


# ── normalize_sql ─────────────────────────────────────────────────────────────


class TestNormalizeSql:
    def test_replaces_integer_literal(self) -> None:
        assert normalize_sql("SELECT * FROM t WHERE id = 42") == "SELECT * FROM T WHERE ID = ?"

    def test_replaces_single_quoted_string(self) -> None:
        assert normalize_sql("SELECT * FROM t WHERE name = 'alice'") == "SELECT * FROM T WHERE NAME = ?"

    def test_replaces_double_quoted_string(self) -> None:
        assert normalize_sql('SELECT * FROM t WHERE name = "alice"') == "SELECT * FROM T WHERE NAME = ?"

    def test_replaces_true(self) -> None:
        assert normalize_sql("SELECT * FROM t WHERE active = TRUE") == "SELECT * FROM T WHERE ACTIVE = ?"

    def test_replaces_false(self) -> None:
        assert normalize_sql("SELECT * FROM t WHERE active = FALSE") == "SELECT * FROM T WHERE ACTIVE = ?"

    def test_replaces_null(self) -> None:
        assert normalize_sql("SELECT * FROM t WHERE deleted_at = NULL") == "SELECT * FROM T WHERE DELETED_AT = ?"

    def test_case_insensitive_true_false_null(self) -> None:
        assert normalize_sql("SELECT * FROM t WHERE x = true AND y = false AND z = null") == (
            "SELECT * FROM T WHERE X = ? AND Y = ? AND Z = ?"
        )

    def test_replaces_multiple_literals(self) -> None:
        sql = "SELECT * FROM t WHERE author_id = 1 AND year = 2024"
        assert normalize_sql(sql) == "SELECT * FROM T WHERE AUTHOR_ID = ? AND YEAR = ?"

    def test_collapses_whitespace(self) -> None:
        assert normalize_sql("SELECT   *   FROM   t") == "SELECT * FROM T"

    def test_two_parametrised_queries_same_normalisation(self) -> None:
        q1 = "SELECT * FROM book WHERE author_id = 1"
        q2 = "SELECT * FROM book WHERE author_id = 99"
        assert normalize_sql(q1) == normalize_sql(q2)

    def test_different_tables_different_normalisation(self) -> None:
        q1 = "SELECT * FROM book WHERE author_id = 1"
        q2 = "SELECT * FROM article WHERE author_id = 1"
        assert normalize_sql(q1) != normalize_sql(q2)


# ── NplusOneDetector — no recommendation cases ───────────────────────────────


class TestNplusOneDetectorNoRecommendation:
    def test_empty_queries_returns_empty(self) -> None:
        assert NplusOneDetector().detect([]) == []

    def test_single_query_no_flag(self) -> None:
        assert NplusOneDetector().detect([_make_query()]) == []

    def test_below_min_count_no_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import django_query_optimizer.detectors.n_plus_one as mod

        monkeypatch.setattr(mod, "N_PLUS_ONE_MIN_COUNT", 5)
        queries = _n_plus_one_queries(4)
        assert NplusOneDetector().detect(queries) == []

    def test_different_patterns_no_flag(self) -> None:
        queries = [
            _make_query("SELECT * FROM book WHERE id = 1"),
            _make_query("SELECT * FROM author WHERE id = 1"),
        ]
        assert NplusOneDetector().detect(queries) == []

    def test_same_pattern_different_call_sites_no_flag(self) -> None:
        """Queries from different call sites are NOT grouped — not an N+1 loop."""
        queries = [
            _make_query(python_file="views.py", python_line=10),
            _make_query(python_file="views.py", python_line=20),
        ]
        assert NplusOneDetector().detect(queries) == []


# ── NplusOneDetector — severity thresholds ───────────────────────────────────


class TestNplusOneDetectorSeverity:
    def test_min_count_triggers_medium(self) -> None:
        queries = _n_plus_one_queries(N_PLUS_ONE_MIN_COUNT)
        recs = NplusOneDetector().detect(queries)
        assert len(recs) == 1
        assert recs[0].severity == Severity.MEDIUM

    def test_high_count_triggers_high(self) -> None:
        queries = _n_plus_one_queries(N_PLUS_ONE_HIGH_COUNT)
        recs = NplusOneDetector().detect(queries)
        assert len(recs) == 1
        assert recs[0].severity == Severity.HIGH

    def test_critical_count_triggers_critical(self) -> None:
        queries = _n_plus_one_queries(N_PLUS_ONE_CRITICAL_COUNT)
        recs = NplusOneDetector().detect(queries)
        assert len(recs) == 1
        assert recs[0].severity == Severity.CRITICAL

    def test_above_critical_still_critical(self) -> None:
        queries = _n_plus_one_queries(N_PLUS_ONE_CRITICAL_COUNT + 5)
        recs = NplusOneDetector().detect(queries)
        assert recs[0].severity == Severity.CRITICAL


# ── NplusOneDetector — recommendation content ────────────────────────────────


class TestNplusOneDetectorContent:
    def test_issue_type_is_n_plus_one(self) -> None:
        recs = NplusOneDetector().detect(_n_plus_one_queries(N_PLUS_ONE_MIN_COUNT))
        assert recs[0].issue_type == "n_plus_one"

    def test_message_contains_count(self) -> None:
        count = 4
        recs = NplusOneDetector().detect(_n_plus_one_queries(count))
        assert str(count) in recs[0].message

    def test_message_contains_normalized_pattern(self) -> None:
        recs = NplusOneDetector().detect(_n_plus_one_queries(N_PLUS_ONE_MIN_COUNT))
        assert "AUTHOR_ID" in recs[0].message

    def test_suggestion_mentions_select_related(self) -> None:
        recs = NplusOneDetector().detect(_n_plus_one_queries(N_PLUS_ONE_MIN_COUNT))
        assert "select_related" in recs[0].suggestion

    def test_suggestion_mentions_prefetch_related(self) -> None:
        recs = NplusOneDetector().detect(_n_plus_one_queries(N_PLUS_ONE_MIN_COUNT))
        assert "prefetch_related" in recs[0].suggestion

    def test_python_file_propagated(self) -> None:
        queries = _n_plus_one_queries(N_PLUS_ONE_MIN_COUNT, python_file="serializers.py")
        recs = NplusOneDetector().detect(queries)
        assert recs[0].python_file == "serializers.py"

    def test_python_line_propagated(self) -> None:
        queries = _n_plus_one_queries(N_PLUS_ONE_MIN_COUNT, python_line=99)
        recs = NplusOneDetector().detect(queries)
        assert recs[0].python_line == 99


# ── NplusOneDetector — multiple groups ───────────────────────────────────────


class TestNplusOneDetectorMultipleGroups:
    def test_two_independent_n_plus_one_groups(self) -> None:
        queries = _n_plus_one_queries(
            N_PLUS_ONE_MIN_COUNT,
            base_sql="SELECT * FROM book WHERE author_id = {i}",
            python_line=10,
        ) + _n_plus_one_queries(
            N_PLUS_ONE_MIN_COUNT,
            base_sql="SELECT * FROM article WHERE tag_id = {i}",
            python_line=20,
        )
        recs = NplusOneDetector().detect(queries)
        assert len(recs) == 2
        issue_types = {r.issue_type for r in recs}
        assert issue_types == {"n_plus_one"}

    def test_mixed_queries_only_n_plus_one_flagged(self) -> None:
        """Unique queries alongside an N+1 group: only the group is flagged."""
        queries = [
            _make_query("SELECT * FROM user WHERE id = 1", python_line=5),
            _make_query("SELECT * FROM user WHERE id = 2", python_line=6),
        ] + _n_plus_one_queries(N_PLUS_ONE_MIN_COUNT, python_line=20)
        recs = NplusOneDetector().detect(queries)
        # Only the group at python_line=20 is flagged (line 5 and 6 differ)
        assert len(recs) == 1
        assert recs[0].python_line == 20


# ── Integration: QueryAnalyzer includes N+1 detection ────────────────────────


class TestQueryAnalyzerIntegration:
    def test_analyzer_detects_n_plus_one(self) -> None:
        from django_query_optimizer.analyzers.query_analyzer import QueryAnalyzer

        queries = _n_plus_one_queries(N_PLUS_ONE_MIN_COUNT)
        recs = QueryAnalyzer(queries).analyze()
        n1_recs = [r for r in recs if r.issue_type == "n_plus_one"]
        assert len(n1_recs) == 1

    def test_analyzer_n_plus_one_and_slow_queries_combined(self) -> None:
        from django_query_optimizer.analyzers.query_analyzer import (
            SLOW_QUERY_THRESHOLD_MS,
            QueryAnalyzer,
        )

        queries = _n_plus_one_queries(N_PLUS_ONE_MIN_COUNT, python_line=10)
        queries[0] = CapturedQuery(
            sql=queries[0].sql,
            duration_ms=SLOW_QUERY_THRESHOLD_MS + 50,
            stack_trace=[],
            python_file="views.py",
            python_line=10,
        )
        recs = QueryAnalyzer(queries).analyze()
        issue_types = {r.issue_type for r in recs}
        assert "n_plus_one" in issue_types
        assert "slow_query" in issue_types
