"""Unit tests for QueryCollector."""

from __future__ import annotations

import traceback
from unittest.mock import MagicMock, patch

import pytest

from django_query_optimizer.collectors.query_collector import (
    CapturedQuery,
    QueryCollector,
    _find_user_frame,
)


class TestCapturedQuery:
    def test_attributes(self) -> None:
        q = CapturedQuery(
            sql="SELECT 1",
            duration_ms=5.0,
            stack_trace=["frame1"],
        )
        assert q.sql == "SELECT 1"
        assert q.duration_ms == 5.0
        assert q.stack_trace == ["frame1"]
        assert q.endpoint == ""
        assert q.python_file == ""
        assert q.python_line == 0


class TestQueryCollector:
    def test_count_starts_at_zero(self) -> None:
        collector = QueryCollector()
        assert collector.count == 0

    def test_count_increases_after_capture(self) -> None:
        collector = QueryCollector()
        collector.queries.append(CapturedQuery(sql="SELECT 1", duration_ms=1.0, stack_trace=[]))
        assert collector.count == 1

    def test_register_is_idempotent(self) -> None:
        """register() must not raise when called multiple times."""
        import django_query_optimizer.collectors.query_collector as mod

        original = mod._REGISTERED
        try:
            mod._REGISTERED = False
            QueryCollector.register()
            QueryCollector.register()  # second call — must be a no-op
        finally:
            mod._REGISTERED = original

    def test_context_manager_adds_and_removes_wrapper(self) -> None:
        mock_connection = MagicMock()
        mock_connection.execute_wrappers = []

        with patch(
            "django_query_optimizer.collectors.query_collector.connection",
            mock_connection,
        ):
            collector = QueryCollector()
            with collector:
                assert len(mock_connection.execute_wrappers) == 1
            assert len(mock_connection.execute_wrappers) == 0

    @pytest.mark.parametrize(
        "duration_ms,expected_duration",
        [
            (0.0, 0.0),
            (50.5, 50.5),
            (999.999, 999.999),
        ],
    )
    def test_capture_records_duration(self, duration_ms: float, expected_duration: float) -> None:
        collector = QueryCollector()

        def fake_execute(*args: object, **kwargs: object) -> None:
            return None

        with patch(
            "django_query_optimizer.collectors.query_collector.time.perf_counter",
            side_effect=[0.0, duration_ms / 1_000],
        ):
            collector._capture(fake_execute, "SELECT 1", [], False, {})

        assert collector.queries[0].duration_ms == pytest.approx(expected_duration, abs=0.01)

    def test_capture_populates_python_file_and_line(self) -> None:
        """_capture must resolve python_file and python_line from the call-stack."""
        collector = QueryCollector()

        def fake_execute(*args: object, **kwargs: object) -> None:
            return None

        collector._capture(fake_execute, "SELECT 1", [], False, {})

        q = collector.queries[0]
        # python_file should point to THIS test file (the closest user frame).
        assert q.python_file != "", "python_file must be set"
        assert q.python_line > 0, "python_line must be positive"
        assert "test_query_collector" in q.python_file


class TestFindUserFrame:
    def test_returns_user_frame(self) -> None:
        """Must return a non-empty filename from user code."""
        frames = traceback.extract_stack()
        filename, lineno = _find_user_frame(frames)
        assert filename != ""
        assert lineno > 0

    def test_skips_django_db_frames(self) -> None:
        """Must skip frames whose path contains 'django/db/'."""
        import os

        summary = traceback.StackSummary.from_list(
            [
                ("/usr/lib/python3.14/os.py", 10, "run", None),
                (f"/app/src/django_query_optimizer{os.sep}collectors{os.sep}query_collector.py", 80, "_capture", None),
                (f"/app{os.sep}myapp{os.sep}views.py", 42, "my_view", None),
            ]
        )
        filename, lineno = _find_user_frame(summary)
        assert "views.py" in filename
        assert lineno == 42

    def test_returns_empty_when_all_frames_internal(self) -> None:
        """Must return ('', 0) when every frame is internal."""
        import os

        summary = traceback.StackSummary.from_list(
            [
                (f"/app{os.sep}django_query_optimizer{os.sep}collectors{os.sep}query_collector.py", 1, "f", None),
                (f"/app{os.sep}django{os.sep}db{os.sep}backends{os.sep}sqlite3.py", 2, "g", None),
            ]
        )
        filename, lineno = _find_user_frame(summary)
        assert filename == ""
        assert lineno == 0
