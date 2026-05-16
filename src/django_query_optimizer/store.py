"""QueryStore — in-memory, thread-safe circular buffer for request records.

This module exposes two public symbols:

``RequestRecord``
    Frozen dataclass representing one captured HTTP request's query data.

``QueryStore``
    Singleton accumulator.  Push ``RequestRecord`` objects after each request,
    then call ``summary()`` to get aggregated statistics for the admin
    dashboard.

Example::

    from django_query_optimizer.store import QueryStore, RequestRecord

    record = RequestRecord(
        endpoint="/api/users/",
        query_count=3,
        total_duration_ms=45.2,
        recommendations=(),
    )
    QueryStore.get().push(record)
    print(QueryStore.get().summary())
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Final

from django_query_optimizer.recommendations.base import ORMRecommendation

MAX_REQUESTS: Final[int] = 500


@dataclass(frozen=True)
class RequestRecord:
    """Snapshot of one HTTP request's query activity.

    Attributes:
        endpoint: ``request.path`` value.
        query_count: Number of SQL queries captured.
        total_duration_ms: Sum of all query durations in milliseconds.
        recommendations: ORM recommendations from ``QueryAnalyzer``.
        timestamp: UTC instant when the record was created.
    """

    endpoint: str
    query_count: int
    total_duration_ms: float
    recommendations: tuple[ORMRecommendation, ...]
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class QueryStore:
    """Singleton, thread-safe store for :class:`RequestRecord` objects.

    Use ``QueryStore.get()`` to obtain the singleton instance and
    ``QueryStore.reset()`` to replace it with a fresh one (useful in tests).

    The buffer has a fixed maximum capacity (``MAX_REQUESTS = 500``).  When
    full, the oldest record is evicted automatically.

    Example::

        store = QueryStore.get()
        store.push(record)
        data = store.summary()
    """

    _class_lock: Lock = Lock()
    _instance: QueryStore | None = None

    def __init__(self, maxlen: int = MAX_REQUESTS) -> None:
        self._records: deque[RequestRecord] = deque(maxlen=maxlen)
        self._write_lock: Lock = Lock()

    # ── Singleton lifecycle ───────────────────────────────────────────────────

    @classmethod
    def get(cls) -> QueryStore:
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Replace the singleton with a fresh instance.

        .. warning::
            For testing only.  Not safe to call in production while requests
            are in-flight.
        """
        with cls._class_lock:
            cls._instance = None

    # ── Buffer operations ─────────────────────────────────────────────────────

    def push(self, record: RequestRecord) -> None:
        """Append *record* to the buffer, evicting the oldest entry if full."""
        with self._write_lock:
            self._records.append(record)

    def all(self) -> list[RequestRecord]:
        """Return a snapshot of the current buffer (oldest first)."""
        with self._write_lock:
            return list(self._records)

    def clear(self) -> None:
        """Remove all records from the buffer."""
        with self._write_lock:
            self._records.clear()

    # ── Aggregation ───────────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Compute aggregated statistics for the admin dashboard.

        Returns:
            A dictionary with the following keys:

            * ``total_requests`` — int
            * ``total_queries`` — int
            * ``avg_queries_per_request`` — float
            * ``slow_requests`` — list[RequestRecord] (total_duration_ms ≥ 500)
            * ``top_endpoints`` — list[dict] (up to 10, sorted by request count)
            * ``recommendations_by_severity`` — dict[str, int]
        """
        records = self.all()
        if not records:
            return {
                "total_requests": 0,
                "total_queries": 0,
                "avg_queries_per_request": 0.0,
                "slow_requests": [],
                "top_endpoints": [],
                "recommendations_by_severity": {},
            }

        total_queries = sum(r.query_count for r in records)
        slow_requests = [r for r in records if r.total_duration_ms >= 500.0]

        # Aggregate per endpoint in a single pass.
        ep_data: dict[str, dict[str, Any]] = defaultdict(lambda: {"request_count": 0, "total_queries": 0})
        for r in records:
            ep_data[r.endpoint]["request_count"] += 1
            ep_data[r.endpoint]["total_queries"] += r.query_count

        top_endpoints = sorted(
            [{"endpoint": ep, **data} for ep, data in ep_data.items()],
            key=lambda x: x["request_count"],
            reverse=True,
        )[:10]

        all_recs = [rec for r in records for rec in r.recommendations]
        sev_counts: Counter[str] = Counter(rec.severity for rec in all_recs)

        return {
            "total_requests": len(records),
            "total_queries": total_queries,
            "avg_queries_per_request": total_queries / len(records),
            "slow_requests": slow_requests,
            "top_endpoints": top_endpoints,
            "recommendations_by_severity": dict(sev_counts),
        }
