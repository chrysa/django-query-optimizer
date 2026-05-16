"""Unit tests for the Django Admin dashboard (QueryLogAdmin)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django_query_optimizer.admin import QueryLog, QueryLogAdmin
from django_query_optimizer.store import QueryStore, RequestRecord

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_record(
    endpoint: str = "/api/orders/",
    query_count: int = 4,
    total_duration_ms: float = 80.0,
) -> RequestRecord:
    return RequestRecord(
        endpoint=endpoint,
        query_count=query_count,
        total_duration_ms=total_duration_ms,
        recommendations=(),
    )


def _make_admin() -> tuple[QueryLogAdmin, MagicMock]:
    """Return (model_admin, mock_site) with each_context stubbed out."""
    from django.contrib.admin.sites import AdminSite

    site = MagicMock(spec=AdminSite)
    site.each_context.return_value = {}
    model_admin = QueryLogAdmin(QueryLog, site)
    return model_admin, site


def _make_request(path: str = "/admin/django_query_optimizer/querylog/") -> MagicMock:
    request = MagicMock()
    request.path = path
    return request


# ── QueryLog model meta ────────────────────────────────────────────────────────


class TestQueryLogModel:
    def test_managed_false(self) -> None:
        assert QueryLog._meta.managed is False

    def test_app_label(self) -> None:
        assert QueryLog._meta.app_label == "django_query_optimizer"

    def test_verbose_name(self) -> None:
        assert str(QueryLog._meta.verbose_name) == "Query Optimizer"


# ── QueryLogAdmin — permission guards ─────────────────────────────────────────


class TestQueryLogAdminPermissions:
    def test_has_add_permission_false(self) -> None:
        model_admin, _ = _make_admin()
        assert model_admin.has_add_permission(_make_request()) is False

    def test_has_change_permission_false(self) -> None:
        model_admin, _ = _make_admin()
        assert model_admin.has_change_permission(_make_request()) is False

    def test_has_delete_permission_false(self) -> None:
        model_admin, _ = _make_admin()
        assert model_admin.has_delete_permission(_make_request()) is False


# ── QueryLogAdmin — changelist_view context injection ─────────────────────────


class TestQueryLogAdminChangelistView:
    def _call_view(self) -> dict:
        """Call changelist_view and capture the template context."""
        model_admin, _ = _make_admin()
        request = _make_request()
        captured: dict = {}

        def fake_template_response(req, tmpl, ctx, **kwargs):  # noqa: ARG001
            captured.update(ctx)
            resp = MagicMock()
            resp.template_name = tmpl
            return resp

        with patch("django_query_optimizer.admin.TemplateResponse", side_effect=fake_template_response):
            model_admin.changelist_view(request)

        return captured

    def test_empty_store_summary_keys_present(self) -> None:
        ctx = self._call_view()
        assert "total_requests" in ctx
        assert "total_queries" in ctx
        assert "avg_queries_per_request" in ctx
        assert "slow_requests" in ctx
        assert "top_endpoints" in ctx
        assert "recommendations_by_severity" in ctx

    def test_empty_store_zero_values(self) -> None:
        ctx = self._call_view()
        assert ctx["total_requests"] == 0
        assert ctx["total_queries"] == 0
        assert ctx["recent_records"] == []

    def test_populated_store_reflects_data(self) -> None:
        QueryStore.get().push(_make_record(endpoint="/api/orders/", query_count=5))
        QueryStore.get().push(_make_record(endpoint="/api/users/", query_count=2))
        ctx = self._call_view()
        assert ctx["total_requests"] == 2
        assert ctx["total_queries"] == 7

    def test_recent_records_newest_first(self) -> None:
        """recent_records must be ordered newest-first (reversed)."""
        r1 = _make_record(endpoint="/a/")
        r2 = _make_record(endpoint="/b/")
        QueryStore.get().push(r1)
        QueryStore.get().push(r2)
        ctx = self._call_view()
        assert ctx["recent_records"][0].endpoint == "/b/"
        assert ctx["recent_records"][1].endpoint == "/a/"

    def test_recent_records_capped_at_50(self) -> None:
        for i in range(60):
            QueryStore.get().push(_make_record(endpoint=f"/{i}/"))
        ctx = self._call_view()
        assert len(ctx["recent_records"]) == 50

    def test_title_set(self) -> None:
        ctx = self._call_view()
        assert ctx["title"] == "Query Optimizer Dashboard"

    def test_uses_custom_template(self) -> None:
        """changelist_view must use the custom dashboard template."""
        model_admin, _ = _make_admin()
        templates_used: list[str] = []

        def fake_template_response(req, tmpl, ctx, **kwargs):  # noqa: ARG001
            templates_used.append(tmpl)
            return MagicMock()

        with patch("django_query_optimizer.admin.TemplateResponse", side_effect=fake_template_response):
            model_admin.changelist_view(_make_request())

        assert templates_used == ["django_query_optimizer/admin/change_list.html"]

    def test_extra_context_merged(self) -> None:
        model_admin, _ = _make_admin()
        captured: dict = {}

        def fake_template_response(req, tmpl, ctx, **kwargs):  # noqa: ARG001
            captured.update(ctx)
            return MagicMock()

        with patch("django_query_optimizer.admin.TemplateResponse", side_effect=fake_template_response):
            model_admin.changelist_view(_make_request(), extra_context={"custom_key": "value"})

        assert captured["custom_key"] == "value"
