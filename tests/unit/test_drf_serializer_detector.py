"""Unit tests for DRFSerializerDetector and helpers."""

from __future__ import annotations

import pytest

from django_query_optimizer.collectors.query_collector import CapturedQuery
from django_query_optimizer.detectors.drf_serializer import (
    DRF_SERIALIZER_HIGH_COUNT,
    DRF_SERIALIZER_MIN_COUNT,
    DRFSerializerDetector,
    _extract_frame_location,
    _find_drf_call_site,
    _has_drf_frame,
    _is_drf_frame,
)
from django_query_optimizer.recommendations.base import Severity

# ── Helpers ───────────────────────────────────────────────────────────────────

_DRF_SERIALIZER_FRAME = (
    '  File "site-packages/rest_framework/serializers.py", line 500, '
    "in to_representation\n    fields = self._readable_fields\n"
)
_DRF_RELATIONS_FRAME = (
    '  File "site-packages/rest_framework/relations.py", line 200, in to_representation\n    return str(value)\n'
)
_DRF_FIELDS_FRAME = (
    '  File "site-packages/rest_framework/fields.py", line 800, in to_representation\n    return value\n'
)
_USER_SERIALIZER_FRAME = (
    '  File "myapp/serializers.py", line 20, in to_representation\n    return super().to_representation(instance)\n'
)
_USER_VIEW_FRAME = (
    '  File "myapp/views.py", line 42, in list\n    return self.get_serializer(queryset, many=True).data\n'
)
_NON_DRF_FRAME = '  File "myapp/utils.py", line 10, in helper\n    pass\n'


def _make_query(
    sql: str = "SELECT * FROM api_author WHERE id = 1",
    stack_trace: list[str] | None = None,
    python_file: str = "myapp/serializers.py",
    python_line: int = 20,
) -> CapturedQuery:
    return CapturedQuery(
        sql=sql,
        duration_ms=1.0,
        stack_trace=stack_trace or [],
        python_file=python_file,
        python_line=python_line,
    )


def _drf_queries(
    n: int,
    base_sql: str = "SELECT * FROM api_author WHERE id = {i}",
    serializer_file: str = "myapp/serializers.py",
    serializer_line: int = 20,
) -> list[CapturedQuery]:
    """Return *n* queries with DRF stack traces from the same call-site."""
    return [
        _make_query(
            sql=base_sql.format(i=i),
            stack_trace=[_USER_VIEW_FRAME, _DRF_SERIALIZER_FRAME, _USER_SERIALIZER_FRAME],
            python_file=serializer_file,
            python_line=serializer_line,
        )
        for i in range(1, n + 1)
    ]


# ── _is_drf_frame ─────────────────────────────────────────────────────────────


class TestIsDrfFrame:
    """_is_drf_frame correctly identifies DRF stack frames."""

    def test_recognises_serializers_frame(self) -> None:
        assert _is_drf_frame(_DRF_SERIALIZER_FRAME) is True

    def test_recognises_relations_frame(self) -> None:
        assert _is_drf_frame(_DRF_RELATIONS_FRAME) is True

    def test_recognises_fields_frame(self) -> None:
        assert _is_drf_frame(_DRF_FIELDS_FRAME) is True

    def test_rejects_user_serializer_frame(self) -> None:
        assert _is_drf_frame(_USER_SERIALIZER_FRAME) is False

    def test_rejects_view_frame(self) -> None:
        assert _is_drf_frame(_USER_VIEW_FRAME) is False

    def test_rejects_non_drf_frame(self) -> None:
        assert _is_drf_frame(_NON_DRF_FRAME) is False

    def test_windows_path_serializers(self) -> None:
        frame = '  File "site-packages\\rest_framework\\serializers.py", line 100, in f\n'
        assert _is_drf_frame(frame) is True

    def test_windows_path_relations(self) -> None:
        frame = '  File "site-packages\\rest_framework\\relations.py", line 50, in g\n'
        assert _is_drf_frame(frame) is True


# ── _extract_frame_location ───────────────────────────────────────────────────


class TestExtractFrameLocation:
    """_extract_frame_location parses file and line from a stack frame string."""

    def test_extracts_path_and_line(self) -> None:
        path, lineno = _extract_frame_location(_DRF_SERIALIZER_FRAME)
        assert "serializers.py" in path
        assert lineno == 500

    def test_extracts_user_frame(self) -> None:
        path, lineno = _extract_frame_location(_USER_SERIALIZER_FRAME)
        assert "myapp/serializers.py" in path
        assert lineno == 20

    def test_empty_string_returns_defaults(self) -> None:
        path, lineno = _extract_frame_location("no file info here")
        assert path == ""
        assert lineno == 0


# ── _has_drf_frame ────────────────────────────────────────────────────────────


class TestHasDrfFrame:
    """_has_drf_frame returns True iff any frame belongs to DRF."""

    def test_true_when_drf_present(self) -> None:
        trace = [_USER_VIEW_FRAME, _DRF_SERIALIZER_FRAME, _USER_SERIALIZER_FRAME]
        assert _has_drf_frame(trace) is True

    def test_false_when_no_drf(self) -> None:
        trace = [_USER_VIEW_FRAME, _NON_DRF_FRAME, _USER_SERIALIZER_FRAME]
        assert _has_drf_frame(trace) is False

    def test_false_for_empty_trace(self) -> None:
        assert _has_drf_frame([]) is False

    def test_true_for_relations_frame(self) -> None:
        assert _has_drf_frame([_DRF_RELATIONS_FRAME]) is True


# ── _find_drf_call_site ───────────────────────────────────────────────────────


class TestFindDrfCallSite:
    """_find_drf_call_site returns the user-code frame preceding DRF code."""

    def test_returns_user_frame_before_drf(self) -> None:
        trace = [_USER_VIEW_FRAME, _DRF_SERIALIZER_FRAME, _USER_SERIALIZER_FRAME]
        path, lineno = _find_drf_call_site(trace)
        assert "views.py" in path
        assert lineno == 42

    def test_returns_empty_when_no_drf_frame(self) -> None:
        trace = [_USER_VIEW_FRAME, _NON_DRF_FRAME]
        path, lineno = _find_drf_call_site(trace)
        assert path == ""
        assert lineno == 0

    def test_returns_empty_for_empty_trace(self) -> None:
        path, lineno = _find_drf_call_site([])
        assert path == ""
        assert lineno == 0

    def test_falls_back_to_drf_frame_when_no_user_frame_before(self) -> None:
        # Only DRF frames in the trace — no user frame precedes them.
        trace = [_DRF_SERIALIZER_FRAME, _DRF_RELATIONS_FRAME]
        path, lineno = _find_drf_call_site(trace)
        assert "serializers.py" in path
        assert lineno == 500


# ── DRFSerializerDetector ─────────────────────────────────────────────────────


class TestDRFSerializerDetectorNoIssues:
    """DRFSerializerDetector returns no recommendations for clean query sets."""

    def test_empty_query_list(self) -> None:
        assert DRFSerializerDetector().detect([]) == []

    def test_no_drf_frames_in_traces(self) -> None:
        queries = [
            _make_query(sql="SELECT 1", stack_trace=[_USER_VIEW_FRAME]),
            _make_query(sql="SELECT 2", stack_trace=[_NON_DRF_FRAME]),
        ]
        assert DRFSerializerDetector().detect(queries) == []

    def test_single_drf_query_below_threshold(self) -> None:
        queries = _drf_queries(1)
        assert DRFSerializerDetector().detect(queries) == []

    def test_different_sql_patterns_not_flagged(self) -> None:
        """Two different SQL patterns from DRF should not be grouped."""
        queries = [
            _make_query(
                sql="SELECT * FROM api_author WHERE id = 1",
                stack_trace=[_USER_VIEW_FRAME, _DRF_SERIALIZER_FRAME],
            ),
            _make_query(
                sql="SELECT * FROM api_book WHERE id = 1",
                stack_trace=[_USER_VIEW_FRAME, _DRF_SERIALIZER_FRAME],
            ),
        ]
        assert DRFSerializerDetector().detect(queries) == []


class TestDRFSerializerDetectorFindsIssues:
    """DRFSerializerDetector flags N+1 patterns from DRF serializer code."""

    def test_two_identical_drf_queries_flagged(self) -> None:
        queries = _drf_queries(DRF_SERIALIZER_MIN_COUNT)
        recs = DRFSerializerDetector().detect(queries)
        assert len(recs) == 1
        assert recs[0].issue_type == "drf_n_plus_one"

    def test_severity_medium_at_min_count(self) -> None:
        queries = _drf_queries(DRF_SERIALIZER_MIN_COUNT)
        recs = DRFSerializerDetector().detect(queries)
        assert recs[0].severity == Severity.MEDIUM

    def test_severity_high_at_high_count(self) -> None:
        queries = _drf_queries(DRF_SERIALIZER_HIGH_COUNT)
        recs = DRFSerializerDetector().detect(queries)
        assert recs[0].severity == Severity.HIGH

    def test_message_contains_count(self) -> None:
        n = 3
        queries = _drf_queries(n)
        recs = DRFSerializerDetector().detect(queries)
        assert str(n) in recs[0].message

    def test_message_contains_normalised_sql(self) -> None:
        queries = _drf_queries(DRF_SERIALIZER_MIN_COUNT)
        recs = DRFSerializerDetector().detect(queries)
        # Normalised SQL replaces literals with ? and uppercases
        assert "API_AUTHOR" in recs[0].message or "api_author" in recs[0].message.lower()

    def test_suggestion_mentions_select_related(self) -> None:
        queries = _drf_queries(DRF_SERIALIZER_MIN_COUNT)
        recs = DRFSerializerDetector().detect(queries)
        assert "select_related" in recs[0].suggestion

    def test_suggestion_mentions_get_queryset(self) -> None:
        queries = _drf_queries(DRF_SERIALIZER_MIN_COUNT)
        recs = DRFSerializerDetector().detect(queries)
        assert "get_queryset" in recs[0].suggestion

    def test_python_file_points_to_user_call_site(self) -> None:
        queries = _drf_queries(DRF_SERIALIZER_MIN_COUNT)
        recs = DRFSerializerDetector().detect(queries)
        # User frame before DRF is the view file
        assert "views.py" in recs[0].python_file

    def test_python_line_matches_user_frame(self) -> None:
        queries = _drf_queries(DRF_SERIALIZER_MIN_COUNT)
        recs = DRFSerializerDetector().detect(queries)
        assert recs[0].python_line == 42

    def test_two_distinct_patterns_produce_two_recs(self) -> None:
        queries = _drf_queries(DRF_SERIALIZER_MIN_COUNT, base_sql="SELECT * FROM api_author WHERE id = {i}")
        queries += _drf_queries(
            DRF_SERIALIZER_MIN_COUNT,
            base_sql="SELECT * FROM api_book WHERE id = {i}",
        )
        recs = DRFSerializerDetector().detect(queries)
        assert len(recs) == 2

    def test_non_drf_queries_excluded_from_grouping(self) -> None:
        """Queries without DRF frames should not contribute to DRF groups."""
        drf_qs = _drf_queries(1)
        non_drf_qs = [
            _make_query(
                sql="SELECT * FROM api_author WHERE id = 99",
                stack_trace=[_USER_VIEW_FRAME],
            )
        ]
        recs = DRFSerializerDetector().detect(drf_qs + non_drf_qs)
        assert recs == []

    def test_relations_frame_also_detected(self) -> None:
        """Queries through rest_framework/relations.py are also flagged."""
        queries = [
            _make_query(
                sql="SELECT * FROM api_author WHERE id = " + str(i),  # noqa: S608
                stack_trace=[_USER_VIEW_FRAME, _DRF_RELATIONS_FRAME],
            )
            for i in range(1, DRF_SERIALIZER_MIN_COUNT + 1)
        ]
        recs = DRFSerializerDetector().detect(queries)
        assert len(recs) == 1
        assert recs[0].issue_type == "drf_n_plus_one"

    def test_fallback_to_python_file_when_no_user_frame(self) -> None:
        """When stack trace lacks a pre-DRF user frame, use query.python_file."""
        queries = [
            _make_query(
                sql="SELECT * FROM api_author WHERE id = " + str(i),  # noqa: S608
                stack_trace=[_DRF_SERIALIZER_FRAME],  # no user frame before DRF
                python_file="myapp/serializers.py",
                python_line=20,
            )
            for i in range(1, DRF_SERIALIZER_MIN_COUNT + 1)
        ]
        recs = DRFSerializerDetector().detect(queries)
        assert len(recs) == 1
        # Falls back to DRF frame itself (500) since no user frame precedes it
        assert recs[0].python_line == 500


class TestDRFSerializerDetectorThresholdPatch:
    """Threshold constants can be monkey-patched."""

    def test_min_count_patch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import django_query_optimizer.detectors.drf_serializer as _d

        monkeypatch.setattr(_d, "DRF_SERIALIZER_MIN_COUNT", 3)
        # Only 2 queries — below patched threshold
        queries = _drf_queries(2)
        assert DRFSerializerDetector().detect(queries) == []

    def test_high_count_patch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import django_query_optimizer.detectors.drf_serializer as _d

        monkeypatch.setattr(_d, "DRF_SERIALIZER_HIGH_COUNT", 3)
        queries = _drf_queries(3)
        recs = DRFSerializerDetector().detect(queries)
        assert recs[0].severity == Severity.HIGH
