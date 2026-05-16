"""Django admin dashboard for django-query-optimizer.

Registers a fake ``QueryLog`` model so that Django's admin shows a
*Query Optimizer* entry under the ``django_query_optimizer`` app.

The view does **not** display database rows.  Instead it reads the
in-process :class:`~django_query_optimizer.store.QueryStore` singleton and
renders aggregated query statistics.

Usage
-----
1. Add ``"django_query_optimizer"`` to ``INSTALLED_APPS``.
2. (Optional) add ``QueryOptimizerMiddleware`` to ``MIDDLEWARE`` so the store
   is automatically populated on every request.
3. Visit ``/admin/django_query_optimizer/querylog/`` in your browser.
"""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.db import models
from django.template.response import TemplateResponse


class QueryLog(models.Model):
    """Proxy model — never creates a database table.

    Exists solely so that Django admin can display the Query Optimizer
    dashboard under a named app section.
    """

    class Meta:
        managed = False
        verbose_name = "Query Optimizer"
        verbose_name_plural = "Query Optimizer"
        app_label = "django_query_optimizer"


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin[QueryLog]):
    """Admin view that renders the Query Optimizer dashboard."""

    change_list_template = "django_query_optimizer/admin/change_list.html"

    # ── Permission guards ────────────────────────────────────────────

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object = None) -> bool:
        return False

    # ── Dashboard view ────────────────────────────────────────────

    def changelist_view(self, request: object, extra_context: dict[str, Any] | None = None) -> TemplateResponse:
        """Render the query optimizer dashboard.

        Injects the :class:`~django_query_optimizer.store.QueryStore` summary
        and the 50 most recent :class:`~django_query_optimizer.store.RequestRecord`
        objects into the template context.
        """
        from django_query_optimizer.store import QueryStore

        store = QueryStore.get()
        all_records = store.all()
        recent_records = list(reversed(all_records[-50:]))

        context: dict[str, Any] = {
            **self.admin_site.each_context(request),  # type: ignore[arg-type]
            **store.summary(),
            "recent_records": recent_records,
            "title": "Query Optimizer Dashboard",
            "opts": self.model._meta,
            "app_label": self.model._meta.app_label,
            **(extra_context or {}),
        }
        return TemplateResponse(request, self.change_list_template, context)  # type: ignore[arg-type]
