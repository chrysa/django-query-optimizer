# ADR-0001 — Query capture via `execute_wrapper`

- **Status:** Accepted
- **Date:** 2026-08-14
- **Context bounded:** collectors

## Context

The library must observe every SQL statement Django's ORM issues, at development
time, in the test suite, and inside an HTTP request — without requiring an HTTP
layer to be present (tests run without a server). Candidate mechanisms:

1. Django `connection.execute_wrappers` (chosen).
2. `django.db.backends.signals` / `connection.queries`.
3. Middleware-only interception.

## Decision

Capture queries with a per-collector callable pushed onto
`connection.execute_wrappers` inside a context manager
(`collectors/query_collector.py`). Middleware and the pytest fixture both wrap a
`QueryCollector`.

## Consequences

- Works in tests with no HTTP and no `DEBUG=True` requirement (unlike
  `connection.queries`, which is gated on `DEBUG` and unbounded in memory).
- `execute_wrappers` is per-connection and connection is thread-local, so each
  request/test needs its own collector instance (documented in the module).
- A full Python stack is extracted per query (`traceback.extract_stack`) to
  resolve the originating user frame — this is the main runtime cost (see
  Kill-test).

## Fatal hypothesis

Per-query `traceback.extract_stack()` overhead stays low enough that the
collector is usable in a real request path, not only in tests.

## Kill-test

Benchmark: a view issuing 500 queries with the collector active must add
**< 15 % wall-clock** vs. the same view with no collector, measured in CI. On
breach: make stack capture opt-in (flag) and default it off in middleware.

## Validation gate

A benchmark test exists in `tests/` and runs in CI before the collector is
recommended for production/middleware use. **Not yet implemented — gate open.**
