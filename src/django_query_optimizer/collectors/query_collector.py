"""Query collector — captures SQL queries at runtime via Django execute_wrapper.

This module exposes two public objects:

``CapturedQuery``
    Immutable snapshot of a single SQL statement, including execution time and
    the Python call-stack at the moment the query was issued.

``QueryCollector``
    A context-manager that hooks into Django's ``connection.execute_wrappers``
    stack for the duration of the ``with`` block, recording every
    ``CapturedQuery`` into ``self.queries``.

    Thread-safety note: each ``QueryCollector`` instance records only the
    queries that flow through *its own* wrapper slot.  Because Django's
    ``execute_wrappers`` list is per-connection (and connections are
    thread-local), concurrent requests each need their own collector instance.

Example::

    from django_query_optimizer.collectors.query_collector import QueryCollector

    with QueryCollector() as col:
        list(MyModel.objects.filter(active=True))

    print(f"{col.count} queries captured")
    for q in col.queries:
        print(f"  {q.duration_ms:.2f} ms — {q.sql[:80]}")
"""

from __future__ import annotations

import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from os import sep
from types import TracebackType
from typing import Final

from django.db import connection

_REGISTRY_LOCK: Final[threading.Lock] = threading.Lock()
_REGISTERED: bool = False

# Path fragments used to identify internal / library frames to skip when
# resolving the user-code origin of a query.
_SKIP_PATHS: Final[tuple[str, ...]] = (
    f"django_query_optimizer{sep}",
    f"django{sep}db{sep}",
    f"django{sep}core{sep}handlers",
    f"django{sep}utils{sep}",
    f"site-packages{sep}django{sep}",
)


def _find_user_frame(frames: traceback.StackSummary) -> tuple[str, int]:
    """Return ``(filename, lineno)`` of the first frame that looks like user code.

    Iterates the call-stack from innermost to outermost, skipping frames that
    belong to Django internals or this library, and returns the first remaining
    frame.  Returns ``("", 0)`` if no user frame is found.
    """
    for frame in reversed(frames):
        filename = frame.filename
        if not any(skip in filename for skip in _SKIP_PATHS):
            return filename, frame.lineno or 0
    return "", 0


@dataclass
class CapturedQuery:
    """A single SQL query captured during a request or test."""

    sql: str
    duration_ms: float
    stack_trace: list[str]
    endpoint: str = ""
    python_file: str = ""
    python_line: int = 0


@dataclass
class QueryCollector:
    """Thread-local collector for SQL queries executed by Django ORM.

    Usage::

        collector = QueryCollector()
        with collector:
            MyModel.objects.all()
        print(collector.queries)
    """

    queries: list[CapturedQuery] = field(default_factory=list)

    def __enter__(self) -> QueryCollector:
        connection.execute_wrappers.append(self._capture)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._capture in connection.execute_wrappers:
            connection.execute_wrappers.remove(self._capture)

    def _capture(
        self,
        execute: Callable[..., object],
        sql: str,
        params: object,
        many: bool,
        context: dict[str, object],
    ) -> object:
        start = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            duration_ms = (time.perf_counter() - start) * 1_000
            frames = traceback.extract_stack()
            python_file, python_line = _find_user_frame(frames)
            self.queries.append(
                CapturedQuery(
                    sql=sql,
                    duration_ms=round(duration_ms, 3),
                    stack_trace=[str(f) for f in frames],
                    python_file=python_file,
                    python_line=python_line,
                )
            )

    @property
    def count(self) -> int:
        """Return the total number of captured queries."""
        return len(self.queries)

    @staticmethod
    def register() -> None:
        """Register the global Django execute_wrapper (called once at bootstrap)."""
        global _REGISTERED  # noqa: PLW0603
        with _REGISTRY_LOCK:
            if _REGISTERED:
                return
            _REGISTERED = True
