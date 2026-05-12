"""Bootstrap — activate middleware and signal handlers (idempotent)."""

from __future__ import annotations

_BOOTSTRAPPED: bool = False


def bootstrap() -> None:
    """Register all django-query-optimizer hooks into the running Django app.

    Safe to call multiple times; subsequent calls are no-ops.
    """
    global _BOOTSTRAPPED  # noqa: PLW0603
    if _BOOTSTRAPPED:
        return

    from django_query_optimizer.collectors.query_collector import QueryCollector

    QueryCollector.register()
    _BOOTSTRAPPED = True
