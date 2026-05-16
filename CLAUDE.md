# CLAUDE.md — django-query-optimizer

> Read `.github/copilot-instructions.md` and `AGENTS.md` before starting any task.
> Updated: 2026-05-16

---

## Purpose

Python library that detects N+1 queries, duplicate queries, slow queries, and missing indexes
in Django applications — at development time, in the test suite, and (planned) in VS Code.

---

## Project State

| Phase | Status |
|---|---|
| 1a — Core (collector, analyzer, slow/duplicate detectors) | ✅ Done |
| 1b — HTTP Middleware (`QueryOptimizerMiddleware`) | 🚧 In progress |
| 1c — Admin dashboard | Planned |
| 2 — ORM Intelligence (N+1, select_related, DRF) | Planned |
| 3 — pytest SARIF report | Planned |
| 4 — VS Code extension (reads SARIF) | Planned |
| 5 — Multi-framework | Planned |

Current version: **0.1.0** (pre-alpha, unreleased on PyPI).

---

## Architecture (quick map)

```
src/django_query_optimizer/
├── __init__.py                 → public API: QueryCollector, QueryAnalyzer,
│                                             ORMRecommendation, QueryOptimizerMiddleware,
│                                             install()
├── _internal/bootstrap.py      → idempotent Django hook registration
├── collectors/query_collector.py → CapturedQuery + QueryCollector (execute_wrapper)
├── middleware/query_collector_middleware.py → per-request collector, sets endpoint
├── analyzers/query_analyzer.py   → slow_query + duplicate_query detectors
├── detectors/                    → Phase 2 (empty)
├── recommendations/base.py       → ORMRecommendation frozen dataclass + Severity enum
├── admin/                        → Phase 1 admin dashboard (empty)
└── testing/pytest_plugin.py      → pytest entry-point + query_collector fixture
```

---

## Key Design Decisions

- **`execute_wrapper`** (not signals or middleware) — lower overhead, works in tests without HTTP.
- **Frozen dataclass** for `ORMRecommendation` — hashable, sortable, immutable.
- **`StrEnum` Severity** — allows `rec.severity == "high"` comparisons without importing the enum.
- **Threshold constants at module level** (`SLOW_QUERY_THRESHOLD_MS`, `DUPLICATE_MIN_COUNT`) — easy to override in tests.
- **pytest plugin registered via `entry-points`** — zero-config activation after `pip install`.

---

## Commands

```bash
make docker-test    # full test suite + coverage (CI target)
make docker-lint    # ruff check + mypy
make lint-all       # lint + typecheck (alias)
make pre-commit     # run all pre-commit hooks on every file
make install-dev    # local dev install (not for test execution)
```

> **Never run pytest / ruff / mypy directly on the host.** Always use `make` targets.

---

## Test Layout

```
tests/
├── conftest.py          # shared fixtures (Django settings module)
├── settings.py          # minimal Django settings for tests
├── unit/
│   ├── test_init.py              # public API surface smoke test
│   ├── test_query_analyzer.py    # QueryAnalyzer detector unit tests
│   ├── test_query_collector.py   # QueryCollector unit tests
│   └── test_recommendations.py   # ORMRecommendation + Severity unit tests
└── integration/                  # Phase 2+ (empty)
```

Coverage threshold: **85%** (enforced by `pytest-cov` with `fail_under = 85`).

---

## Adding a New Detector

1. Add a `_detect_<name>` private method in `QueryAnalyzer`.
2. Call it from `analyze()` and append results to the list.
3. Use an existing `Severity` level or add a new one to the `Severity` enum if justified.
4. Write a matching test class in `tests/unit/test_query_analyzer.py`.
5. Update the detector table in `README.md`.

---

## Conventions

- Public API exports live in `__init__.py.__all__` — nothing else is considered stable.
- No breaking changes without a major version bump.
- All type annotations must pass `mypy --strict`.
- Commit identity: `user.name=chrysa`, `user.email=greau.anthony+chrysa@gmail.com`.
