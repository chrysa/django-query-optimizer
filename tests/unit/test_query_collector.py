"""Unit tests for QueryCollector."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from django_query_optimizer.collectors.query_collector import (
    CapturedQuery,
    QueryCollector,
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
