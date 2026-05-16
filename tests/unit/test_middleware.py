"""Unit tests for QueryOptimizerMiddleware."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django_query_optimizer.middleware.query_collector_middleware import QueryOptimizerMiddleware


def _make_request(path: str = "/api/orders/") -> MagicMock:
    """Return a minimal mock Django HttpRequest."""
    request = MagicMock()
    request.path = path
    return request


def _make_response() -> MagicMock:
    return MagicMock()


class TestQueryOptimizerMiddlewareEndpoint:
    def test_sets_endpoint_on_captured_queries(self) -> None:
        """Middleware must populate query.endpoint with request.path."""
        from django_query_optimizer.collectors.query_collector import CapturedQuery

        captured: list[CapturedQuery] = []

        def fake_get_response(request: MagicMock) -> MagicMock:
            # Simulate a query captured during view execution.
            captured.append(CapturedQuery(sql="SELECT 1", duration_ms=1.0, stack_trace=[]))
            return _make_response()

        middleware = QueryOptimizerMiddleware(fake_get_response)

        # Patch QueryCollector so it yields the pre-populated list.
        with patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector") as mock_collector:
            instance = MagicMock()
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            instance.queries = captured
            mock_collector.return_value = instance

            request = _make_request("/api/orders/")
            middleware(request)

        assert captured[0].endpoint == "/api/orders/"

    def test_endpoint_reflects_request_path(self) -> None:
        """Different paths produce different endpoint values."""
        from django_query_optimizer.collectors.query_collector import CapturedQuery

        for path in ("/admin/", "/api/users/42/", "/"):
            captured = [CapturedQuery(sql="SELECT 1", duration_ms=1.0, stack_trace=[])]

            def fake_get_response(request: MagicMock) -> MagicMock:  # noqa: B023
                return _make_response()

            middleware = QueryOptimizerMiddleware(fake_get_response)

            with patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector") as mock_collector:
                instance = MagicMock()
                instance.__enter__ = MagicMock(return_value=instance)
                instance.__exit__ = MagicMock(return_value=False)
                instance.queries = captured
                mock_collector.return_value = instance

                request = _make_request(path)
                middleware(request)

            assert captured[0].endpoint == path

    def test_no_queries_no_error(self) -> None:
        """Middleware must not raise when no queries are captured."""
        middleware = QueryOptimizerMiddleware(lambda req: _make_response())

        with patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector") as mock_collector:
            instance = MagicMock()
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            instance.queries = []
            mock_collector.return_value = instance

            middleware(_make_request())  # must not raise


class TestQueryOptimizerMiddlewareAttachment:
    def test_attaches_collector_to_request(self) -> None:
        """After the call, request.query_collector must be the collector instance."""
        middleware = QueryOptimizerMiddleware(lambda req: _make_response())

        with patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector") as mock_collector:
            instance = MagicMock()
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            instance.queries = []
            mock_collector.return_value = instance

            request = _make_request()
            middleware(request)

        assert request.query_collector is instance

    def test_new_collector_per_request(self) -> None:
        """A fresh QueryCollector must be instantiated for every request."""
        middleware = QueryOptimizerMiddleware(lambda req: _make_response())

        with patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector") as mock_collector:
            instance = MagicMock()
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            instance.queries = []
            mock_collector.return_value = instance

            middleware(_make_request())
            middleware(_make_request())

        assert mock_collector.call_count == 2


class TestQueryOptimizerMiddlewareResponse:
    def test_returns_get_response_result(self) -> None:
        """Middleware must return exactly what get_response returns."""
        expected = _make_response()
        middleware = QueryOptimizerMiddleware(lambda req: expected)

        with patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector") as mock_collector:
            instance = MagicMock()
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            instance.queries = []
            mock_collector.return_value = instance

            result = middleware(_make_request())

        assert result is expected
