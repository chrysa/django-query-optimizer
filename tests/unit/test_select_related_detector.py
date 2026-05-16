"""Unit tests for SelectRelatedDetector and helpers."""

from __future__ import annotations

from django_query_optimizer.collectors.query_collector import CapturedQuery
from django_query_optimizer.detectors.select_related import (
    SELECT_RELATED_MIN_COUNT,
    SelectRelatedDetector,
    _looks_like_fk_lookup,
    _table_to_field,
)
from django_query_optimizer.recommendations.base import Severity


def _q(sql: str, python_file: str = "views.py", python_line: int = 10) -> CapturedQuery:
    return CapturedQuery(
        sql=sql,
        duration_ms=1.0,
        stack_trace=[],
        python_file=python_file,
        python_line=python_line,
    )


# ── _looks_like_fk_lookup ──────────────────────────────────────────────────


class TestLooksLikeFkLookup:
    """_looks_like_fk_lookup correctly identifies FK-lookup patterns."""

    def test_simple_select_where(self) -> None:
        sql = "SELECT * FROM author WHERE id = ?"
        assert _looks_like_fk_lookup(sql) is not None

    def test_normalised_uppercase(self) -> None:
        sql = "SELECT * FROM BOOK_AUTHOR WHERE ID = ?"
        assert _looks_like_fk_lookup(sql) is not None

    def test_quoted_table(self) -> None:
        sql = 'SELECT * FROM "auth_user" WHERE "id" = ?'
        assert _looks_like_fk_lookup(sql) is not None

    def test_with_schema_prefix(self) -> None:
        sql = "SELECT * FROM public.author WHERE id = ?"
        assert _looks_like_fk_lookup(sql) is not None

    def test_captures_table_name(self) -> None:
        sql = "SELECT * FROM book_author WHERE id = ?"
        match = _looks_like_fk_lookup(sql)
        assert match is not None
        assert match.group("table").lower() == "book_author"

    def test_captures_column_name(self) -> None:
        sql = "SELECT * FROM author WHERE author_id = ?"
        match = _looks_like_fk_lookup(sql)
        assert match is not None
        assert match.group("col").lower() == "author_id"

    def test_rejects_join_query(self) -> None:
        sql = "SELECT * FROM book JOIN author ON book.author_id = author.id WHERE book.id = ?"
        assert _looks_like_fk_lookup(sql) is None

    def test_rejects_multi_condition(self) -> None:
        sql = "SELECT * FROM author WHERE id = ? AND active = ?"
        assert _looks_like_fk_lookup(sql) is None

    def test_rejects_insert(self) -> None:
        sql = "INSERT INTO author (name) VALUES (?)"
        assert _looks_like_fk_lookup(sql) is None

    def test_rejects_update(self) -> None:
        sql = "UPDATE author SET name = ? WHERE id = ?"
        assert _looks_like_fk_lookup(sql) is None

    def test_rejects_no_where(self) -> None:
        sql = "SELECT * FROM author"
        assert _looks_like_fk_lookup(sql) is None

    def test_rejects_where_non_eq(self) -> None:
        sql = "SELECT * FROM author WHERE id > ?"
        assert _looks_like_fk_lookup(sql) is None


# ── _table_to_field ────────────────────────────────────────────────────────


class TestTableToField:
    """_table_to_field converts table names to likely Django field names."""

    def test_simple_table(self) -> None:
        assert _table_to_field("author") == "author"

    def test_app_prefix_stripped(self) -> None:
        assert _table_to_field("myapp_author") == "author"

    def test_multi_part_kept(self) -> None:
        # "auth_user" has 2 parts but 'user' has no underscore → stripped to 'user'
        assert _table_to_field("auth_user") == "user"

    def test_three_parts_kept(self) -> None:
        # "myapp_blog_post" → parts = ["myapp", "blog_post"] → "blog_post" contains _ → keep full lowercase
        assert _table_to_field("myapp_blog_post") == "myapp_blog_post"

    def test_uppercase_input(self) -> None:
        assert _table_to_field("BOOK_AUTHOR") == "author"

    def test_no_prefix(self) -> None:
        assert _table_to_field("order") == "order"


# ── SelectRelatedDetector — no recommendations ────────────────────────────


class TestSelectRelatedDetectorNoRecommendation:
    """Detector produces no output when count < threshold."""

    def test_empty_queries(self) -> None:
        assert SelectRelatedDetector().detect([]) == []

    def test_single_fk_lookup(self) -> None:
        queries = [_q("SELECT * FROM author WHERE id = 1")]
        assert SelectRelatedDetector().detect(queries) == []

    def test_count_below_threshold(self) -> None:
        queries = [_q(f"SELECT * FROM author WHERE id = {i}") for i in range(SELECT_RELATED_MIN_COUNT - 1)]  # noqa: S608
        assert SelectRelatedDetector().detect(queries) == []

    def test_non_fk_queries_ignored(self) -> None:
        queries = [
            _q("SELECT * FROM book JOIN author ON book.author_id = author.id"),
            _q("SELECT * FROM book JOIN author ON book.author_id = author.id"),
        ]
        assert SelectRelatedDetector().detect(queries) == []

    def test_different_call_sites_not_grouped(self) -> None:
        queries = [
            _q("SELECT * FROM author WHERE id = 1", python_line=10),
            _q("SELECT * FROM author WHERE id = 2", python_line=20),
        ]
        # Two different call-sites → each has count 1 → no recommendation
        assert SelectRelatedDetector().detect(queries) == []


# ── SelectRelatedDetector — detection ─────────────────────────────────────


class TestSelectRelatedDetectorDetection:
    """Detector flags FK-lookup groups at or above threshold."""

    def test_detects_repeated_fk_lookup(self) -> None:
        queries = [
            _q("SELECT * FROM author WHERE id = 1"),
            _q("SELECT * FROM author WHERE id = 2"),
        ]
        recs = SelectRelatedDetector().detect(queries)
        assert len(recs) == 1

    def test_issue_type(self) -> None:
        queries = [_q(f"SELECT * FROM author WHERE id = {i}") for i in range(3)]  # noqa: S608
        recs = SelectRelatedDetector().detect(queries)
        assert recs[0].issue_type == "missing_select_related"

    def test_severity_medium_below_ten(self) -> None:
        queries = [_q(f"SELECT * FROM author WHERE id = {i}") for i in range(5)]  # noqa: S608
        recs = SelectRelatedDetector().detect(queries)
        assert recs[0].severity == Severity.MEDIUM

    def test_severity_high_at_ten(self) -> None:
        queries = [_q(f"SELECT * FROM author WHERE id = {i}") for i in range(10)]  # noqa: S608
        recs = SelectRelatedDetector().detect(queries)
        assert recs[0].severity == Severity.HIGH

    def test_table_name_in_message(self) -> None:
        queries = [_q(f"SELECT * FROM book_author WHERE id = {i}") for i in range(2)]  # noqa: S608
        recs = SelectRelatedDetector().detect(queries)
        assert "book_author" in recs[0].message.upper() or "BOOK_AUTHOR" in recs[0].message.upper()

    def test_suggestion_contains_select_related(self) -> None:
        queries = [_q(f"SELECT * FROM author WHERE id = {i}") for i in range(2)]  # noqa: S608
        recs = SelectRelatedDetector().detect(queries)
        assert "select_related" in recs[0].suggestion

    def test_field_hint_in_suggestion(self) -> None:
        queries = [_q(f"SELECT * FROM myapp_author WHERE id = {i}") for i in range(2)]  # noqa: S608
        recs = SelectRelatedDetector().detect(queries)
        assert "author" in recs[0].suggestion

    def test_python_file_propagated(self) -> None:
        queries = [_q(f"SELECT * FROM author WHERE id = {i}", python_file="serializers.py") for i in range(2)]  # noqa: S608
        recs = SelectRelatedDetector().detect(queries)
        assert recs[0].python_file == "serializers.py"

    def test_python_line_propagated(self) -> None:
        queries = [_q(f"SELECT * FROM author WHERE id = {i}", python_line=42) for i in range(2)]  # noqa: S608
        recs = SelectRelatedDetector().detect(queries)
        assert recs[0].python_line == 42

    def test_count_in_message(self) -> None:
        queries = [_q(f"SELECT * FROM author WHERE id = {i}") for i in range(4)]  # noqa: S608
        recs = SelectRelatedDetector().detect(queries)
        assert "4" in recs[0].message


# ── SelectRelatedDetector — multiple groups ───────────────────────────────


class TestSelectRelatedDetectorMultipleGroups:
    """Multiple independent FK-lookup groups produce separate recommendations."""

    def test_two_tables_produce_two_recs(self) -> None:
        queries = [
            _q("SELECT * FROM author WHERE id = 1"),
            _q("SELECT * FROM author WHERE id = 2"),
            _q("SELECT * FROM publisher WHERE id = 1"),
            _q("SELECT * FROM publisher WHERE id = 2"),
        ]
        recs = SelectRelatedDetector().detect(queries)
        assert len(recs) == 2

    def test_two_call_sites_same_table_produce_two_recs(self) -> None:
        queries = [
            _q("SELECT * FROM author WHERE id = 1", python_line=10),
            _q("SELECT * FROM author WHERE id = 2", python_line=10),
            _q("SELECT * FROM author WHERE id = 3", python_line=20),
            _q("SELECT * FROM author WHERE id = 4", python_line=20),
        ]
        recs = SelectRelatedDetector().detect(queries)
        assert len(recs) == 2

    def test_mixed_fk_and_non_fk(self) -> None:
        queries = [
            _q("SELECT * FROM author WHERE id = 1"),
            _q("SELECT * FROM author WHERE id = 2"),
            _q("SELECT * FROM book JOIN author ON book.author_id = author.id"),
            _q("SELECT * FROM book JOIN author ON book.author_id = author.id"),
        ]
        recs = SelectRelatedDetector().detect(queries)
        # Only the FK-lookup pattern triggers
        assert len(recs) == 1
        assert recs[0].issue_type == "missing_select_related"


# ── Integration with QueryAnalyzer ────────────────────────────────────────


class TestQueryAnalyzerIntegration:
    """SelectRelatedDetector is wired into QueryAnalyzer.analyze()."""

    def test_analyzer_includes_select_related_recs(self) -> None:
        from django_query_optimizer.analyzers.query_analyzer import QueryAnalyzer

        queries = [
            _q("SELECT * FROM author WHERE id = 1"),
            _q("SELECT * FROM author WHERE id = 2"),
        ]
        recs = QueryAnalyzer(queries).analyze()
        issue_types = [r.issue_type for r in recs]
        assert "missing_select_related" in issue_types

    def test_analyzer_no_false_positive_on_joins(self) -> None:
        from django_query_optimizer.analyzers.query_analyzer import QueryAnalyzer

        queries = [
            _q("SELECT * FROM book JOIN author ON book.author_id = author.id WHERE book.id = 1"),
            _q("SELECT * FROM book JOIN author ON book.author_id = author.id WHERE book.id = 2"),
        ]
        recs = QueryAnalyzer(queries).analyze()
        select_related_recs = [r for r in recs if r.issue_type == "missing_select_related"]
        assert select_related_recs == []
