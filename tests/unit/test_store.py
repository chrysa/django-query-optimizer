"""Unit tests for QueryStore and RequestRecord."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

import pytest

from django_query_optimizer.recommendations.base import ORMRecommendation, Severity
from django_query_optimizer.store import QueryStore, RequestRecord

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_record(
    endpoint: str = "/api/test/",
    query_count: int = 3,
    total_duration_ms: float = 50.0,
    recommendations: tuple[ORMRecommendation, ...] = (),
) -> RequestRecord:
    return RequestRecord(
        endpoint=endpoint,
        query_count=query_count,
        total_duration_ms=total_duration_ms,
        recommendations=recommendations,
    )


def _make_rec(severity: Severity = Severity.HIGH) -> ORMRecommendation:
    return ORMRecommendation(
        issue_type="slow_query",
        severity=severity,
        message="test",
        suggestion="use an index",
    )


# ── RequestRecord ──────────────────────────────────────────────────────────────


class TestRequestRecord:
    def test_frozen(self) -> None:
        """RequestRecord must be immutable."""
        record = _make_record()
        with pytest.raises(AttributeError):
            record.query_count = 99  # type: ignore[misc]

    def test_default_timestamp_is_utc(self) -> None:
        record = _make_record()
        assert record.timestamp.tzinfo is UTC

    def test_custom_timestamp(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=UTC)
        record = RequestRecord(
            endpoint="/",
            query_count=0,
            total_duration_ms=0.0,
            recommendations=(),
            timestamp=ts,
        )
        assert record.timestamp == ts


# ── QueryStore — singleton ─────────────────────────────────────────────────────


class TestQueryStoreSingleton:
    def test_get_returns_same_instance(self) -> None:
        a = QueryStore.get()
        b = QueryStore.get()
        assert a is b

    def test_reset_creates_new_instance(self) -> None:
        first = QueryStore.get()
        QueryStore.reset()
        second = QueryStore.get()
        assert first is not second

    def test_get_after_reset_is_empty(self) -> None:
        store = QueryStore.get()
        store.push(_make_record())
        QueryStore.reset()
        assert QueryStore.get().all() == []


# ── QueryStore — buffer operations ────────────────────────────────────────────


class TestQueryStoreBuffer:
    def test_push_and_all(self) -> None:
        store = QueryStore.get()
        r1 = _make_record(endpoint="/a/")
        r2 = _make_record(endpoint="/b/")
        store.push(r1)
        store.push(r2)
        records = store.all()
        assert records == [r1, r2]

    def test_all_returns_snapshot(self) -> None:
        """Mutating the returned list must not affect the store."""
        store = QueryStore.get()
        store.push(_make_record())
        snapshot = store.all()
        snapshot.clear()
        assert len(store.all()) == 1

    def test_clear_empties_buffer(self) -> None:
        store = QueryStore.get()
        store.push(_make_record())
        store.push(_make_record())
        store.clear()
        assert store.all() == []

    def test_max_capacity_evicts_oldest(self) -> None:
        """When full, the oldest record must be evicted."""
        store = QueryStore(maxlen=3)
        records = [_make_record(endpoint=f"/{i}/") for i in range(4)]
        for r in records:
            store.push(r)
        remaining = store.all()
        assert len(remaining) == 3
        # The first record (/0/) must have been evicted.
        assert remaining[0].endpoint == "/1/"
        assert remaining[-1].endpoint == "/3/"


# ── QueryStore — summary (empty store) ───────────────────────────────────────


class TestQueryStoreSummaryEmpty:
    def test_empty_store_returns_zero_stats(self) -> None:
        summary = QueryStore.get().summary()
        assert summary["total_requests"] == 0
        assert summary["total_queries"] == 0
        assert summary["avg_queries_per_request"] == 0.0
        assert summary["slow_requests"] == []
        assert summary["top_endpoints"] == []
        assert summary["recommendations_by_severity"] == {}


# ── QueryStore — summary (populated store) ───────────────────────────────────


class TestQueryStoreSummaryPopulated:
    def test_total_requests_and_queries(self) -> None:
        store = QueryStore.get()
        store.push(_make_record(query_count=2))
        store.push(_make_record(query_count=5))
        s = store.summary()
        assert s["total_requests"] == 2
        assert s["total_queries"] == 7

    def test_avg_queries_per_request(self) -> None:
        store = QueryStore.get()
        store.push(_make_record(query_count=4))
        store.push(_make_record(query_count=6))
        assert store.summary()["avg_queries_per_request"] == pytest.approx(5.0)

    def test_slow_requests_threshold_500ms(self) -> None:
        store = QueryStore.get()
        fast = _make_record(total_duration_ms=499.9)
        slow = _make_record(total_duration_ms=500.0)
        very_slow = _make_record(total_duration_ms=1200.0)
        for r in (fast, slow, very_slow):
            store.push(r)
        slow_list = store.summary()["slow_requests"]
        assert fast not in slow_list
        assert slow in slow_list
        assert very_slow in slow_list

    def test_top_endpoints_sorted_by_request_count(self) -> None:
        store = QueryStore.get()
        store.push(_make_record(endpoint="/a/"))
        store.push(_make_record(endpoint="/b/"))
        store.push(_make_record(endpoint="/b/"))
        store.push(_make_record(endpoint="/c/"))
        store.push(_make_record(endpoint="/c/"))
        store.push(_make_record(endpoint="/c/"))
        top = store.summary()["top_endpoints"]
        assert top[0]["endpoint"] == "/c/"
        assert top[0]["request_count"] == 3
        assert top[1]["endpoint"] == "/b/"

    def test_top_endpoints_max_10(self) -> None:
        store = QueryStore.get()
        for i in range(15):
            store.push(_make_record(endpoint=f"/{i}/"))
        assert len(store.summary()["top_endpoints"]) == 10

    def test_top_endpoints_total_queries(self) -> None:
        store = QueryStore.get()
        store.push(_make_record(endpoint="/api/", query_count=3))
        store.push(_make_record(endpoint="/api/", query_count=7))
        ep = store.summary()["top_endpoints"][0]
        assert ep["endpoint"] == "/api/"
        assert ep["total_queries"] == 10
        assert ep["request_count"] == 2

    def test_recommendations_by_severity(self) -> None:
        store = QueryStore.get()
        rec_high = _make_rec(Severity.HIGH)
        rec_medium = _make_rec(Severity.MEDIUM)
        store.push(_make_record(recommendations=(rec_high, rec_high)))
        store.push(_make_record(recommendations=(rec_medium,)))
        sev = store.summary()["recommendations_by_severity"]
        assert sev[Severity.HIGH] == 2
        assert sev[Severity.MEDIUM] == 1


# ── Thread-safety ──────────────────────────────────────────────────────────────


class TestQueryStoreThreadSafety:
    def test_concurrent_pushes_do_not_lose_records(self) -> None:
        """All pushes from concurrent threads must be recorded."""
        n_threads = 10
        n_records_per_thread = 20
        store_capacity = n_threads * n_records_per_thread

        # Use a store with enough capacity so nothing is evicted.
        store_big = QueryStore(maxlen=store_capacity)
        errors: list[Exception] = []

        def push_many() -> None:
            try:
                for _ in range(n_records_per_thread):
                    store_big.push(_make_record())
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=push_many) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        assert len(store_big.all()) == store_capacity
