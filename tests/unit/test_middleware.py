"""Unit tests for QueryOptimizerMiddleware."""

from __future__ import annotations

from typing import Any

from pytest_mock import MockerFixture

from django_query_optimizer.middleware.query_collector_middleware import QueryOptimizerMiddleware


def _make_request(mocker: MockerFixture, path: str = "/api/orders/") -> Any:
    """Return a minimal mock Django HttpRequest."""
    request = mocker.MagicMock()
    request.path = path
    return request


def _make_response(mocker: MockerFixture) -> Any:
    return mocker.MagicMock()


class TestQueryOptimizerMiddlewareEndpoint:
    def test_sets_endpoint_on_captured_queries(self, mocker: MockerFixture) -> None:
        """Middleware must populate query.endpoint with request.path."""
        from django_query_optimizer.collectors.query_collector import CapturedQuery

        captured: list[CapturedQuery] = []

        def fake_get_response(request: Any) -> Any:
            # Simulate a query captured during view execution.
            captured.append(CapturedQuery(sql="SELECT 1", duration_ms=1.0, stack_trace=[]))
            return _make_response(mocker)

        middleware = QueryOptimizerMiddleware(fake_get_response)

        # Patch QueryCollector so it yields the pre-populated list.
        mock_collector = mocker.patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector")
        instance = mocker.MagicMock()
        instance.__enter__ = mocker.MagicMock(return_value=instance)
        instance.__exit__ = mocker.MagicMock(return_value=False)
        instance.queries = captured
        mock_collector.return_value = instance

        request = _make_request(mocker, "/api/orders/")
        middleware(request)

        assert captured[0].endpoint == "/api/orders/"

    def test_endpoint_reflects_request_path(self, mocker: MockerFixture) -> None:
        """Different paths produce different endpoint values."""
        from django_query_optimizer.collectors.query_collector import CapturedQuery

        for path in ("/admin/", "/api/users/42/", "/"):
            captured = [CapturedQuery(sql="SELECT 1", duration_ms=1.0, stack_trace=[])]

            def fake_get_response(request: Any) -> Any:
                return _make_response(mocker)

            middleware = QueryOptimizerMiddleware(fake_get_response)

            mock_collector = mocker.patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector")
            instance = mocker.MagicMock()
            instance.__enter__ = mocker.MagicMock(return_value=instance)
            instance.__exit__ = mocker.MagicMock(return_value=False)
            instance.queries = captured
            mock_collector.return_value = instance

            request = _make_request(mocker, path)
            middleware(request)

            assert captured[0].endpoint == path

    def test_no_queries_no_error(self, mocker: MockerFixture) -> None:
        """Middleware must not raise when no queries are captured."""
        middleware = QueryOptimizerMiddleware(lambda req: _make_response(mocker))

        mock_collector = mocker.patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector")
        instance = mocker.MagicMock()
        instance.__enter__ = mocker.MagicMock(return_value=instance)
        instance.__exit__ = mocker.MagicMock(return_value=False)
        instance.queries = []
        mock_collector.return_value = instance

        middleware(_make_request(mocker))  # must not raise


class TestQueryOptimizerMiddlewareAttachment:
    def test_attaches_collector_to_request(self, mocker: MockerFixture) -> None:
        """After the call, request.query_collector must be the collector instance."""
        middleware = QueryOptimizerMiddleware(lambda req: _make_response(mocker))

        mock_collector = mocker.patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector")
        instance = mocker.MagicMock()
        instance.__enter__ = mocker.MagicMock(return_value=instance)
        instance.__exit__ = mocker.MagicMock(return_value=False)
        instance.queries = []
        mock_collector.return_value = instance

        request = _make_request(mocker)
        middleware(request)

        assert request.query_collector is instance

    def test_new_collector_per_request(self, mocker: MockerFixture) -> None:
        """A fresh QueryCollector must be instantiated for every request."""
        middleware = QueryOptimizerMiddleware(lambda req: _make_response(mocker))

        mock_collector = mocker.patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector")
        instance = mocker.MagicMock()
        instance.__enter__ = mocker.MagicMock(return_value=instance)
        instance.__exit__ = mocker.MagicMock(return_value=False)
        instance.queries = []
        mock_collector.return_value = instance

        middleware(_make_request(mocker))
        middleware(_make_request(mocker))

        assert mock_collector.call_count == 2


class TestQueryOptimizerMiddlewareResponse:
    def test_returns_get_response_result(self, mocker: MockerFixture) -> None:
        """Middleware must return exactly what get_response returns."""
        expected = _make_response(mocker)
        middleware = QueryOptimizerMiddleware(lambda req: expected)

        mock_collector = mocker.patch("django_query_optimizer.middleware.query_collector_middleware.QueryCollector")
        instance = mocker.MagicMock()
        instance.__enter__ = mocker.MagicMock(return_value=instance)
        instance.__exit__ = mocker.MagicMock(return_value=False)
        instance.queries = []
        mock_collector.return_value = instance

        result = middleware(_make_request(mocker))

        assert result is expected
