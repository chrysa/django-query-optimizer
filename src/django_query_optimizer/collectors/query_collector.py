"""Query collector - captures SQL queries at runtime via Django execute_wrapper."""

from __future__ import annotations

import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from types import TracebackType
from typing import Final

_REGISTRY_LOCK: Final[threading.Lock] = threading.Lock()
_REGISTERED: bool = False


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
        from django.db import connection

        connection.execute_wrappers.append(self._capture)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        from django.db import connection

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
            self.queries.append(
                CapturedQuery(
                    sql=sql,
                    duration_ms=round(duration_ms, 3),
                    stack_trace=[str(f) for f in frames],
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
