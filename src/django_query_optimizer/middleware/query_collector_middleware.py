"""QueryOptimizerMiddleware — per-request SQL query collection.

This middleware wraps every HTTP request in a :class:`QueryCollector` so that
``endpoint``, ``python_file``, and ``python_line`` are automatically populated
on every :class:`~django_query_optimizer.collectors.query_collector.CapturedQuery`.

Setup
-----
Add it to ``MIDDLEWARE`` in your **development** settings, after
``SessionMiddleware``::

    MIDDLEWARE = [
        ...
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django_query_optimizer.middleware.query_collector_middleware.QueryOptimizerMiddleware",
        ...
    ]

After the response is built the middleware:

1. Sets ``query.endpoint = request.path`` on every captured query.
2. Attaches the collector to ``request.query_collector`` so downstream code
   (views, signals, the Admin dashboard) can inspect it::

       def my_view(request):
           qs = MyModel.objects.all()
           response = render(request, "list.html", {"objects": qs})
           # middleware will set endpoint + attach collector after this returns
           return response

       # In a signal / admin view:
       collector = getattr(request, "query_collector", None)
       if collector:
           print(f"{collector.count} queries for {request.path}")

.. warning::
   Do **not** add this middleware in production settings.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from django_query_optimizer.collectors.query_collector import QueryCollector

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class QueryOptimizerMiddleware:
    """Django WSGI/ASGI middleware that wraps each request in a :class:`QueryCollector`.

    After the response is built it:

    * Sets ``query.endpoint`` to ``request.path`` on every captured query.
    * Attaches the collector to ``request.query_collector``.

    Thread-safety: a **new** ``QueryCollector`` is created for every request,
    so concurrent requests never share a collector.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        collector = QueryCollector()
        with collector:
            response = self._get_response(request)

        endpoint = request.path
        for query in collector.queries:
            query.endpoint = endpoint

        # Attach for downstream access (admin dashboard, signals, tests).
        request.query_collector = collector  # type: ignore[attr-defined]

        return response
