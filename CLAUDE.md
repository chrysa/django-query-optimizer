# CLAUDE.md — django-query-optimizer

> Read `.github/copilot-instructions.md` and `AGENTS.md` before starting any task.
> Updated: 2026-05-16

## Purpose

Python library that detects N+1 queries, duplicate queries, slow queries, and missing indexes
in Django applications — at development time, in the test suite, and in VS Code (Phase 4 in progress).

---

## Project State

| Phase | Status |
|---|---|
| 1a — Core (collector, analyzer, slow/duplicate detectors) | ✅ Done |
| 1b — HTTP Middleware (`QueryOptimizerMiddleware`) | ✅ Done |
| 1c — Admin dashboard | ✅ Done |
| 2a — N+1 detector (`NplusOneDetector`) | ✅ Done |
| 2b — DRF serializer N+1 detector (`DRFSerializerDetector`) | ✅ Done |
| 2c — FK detector (`SelectRelatedDetector`) | ✅ Done |
| 2d — Query scoring (`QueryScorer`) | ✅ Done |
| 3 — pytest SARIF report + `RegressionDetector` | ✅ Done |
| 4 — VS Code extension (reads SARIF) | 🚧 In Progress |
| 5 — Multi-framework | Planned |

Current version: **0.1.0** (pre-alpha, unreleased on PyPI).

**Phase 4 repos:**
- Pytest plugin: PR [#22](https://github.com/chrysa/django-query-optimizer/pull/22) on `feat/phase4-sarif-output`
- VS Code extension: [`chrysa/django-query-optimizer-vscode`](https://github.com/chrysa/django-query-optimizer-vscode)

---

## Architecture (quick map)

```
src/django_query_optimizer/
├── __init__.py                 → public API: QueryCollector, QueryAnalyzer,
│                                             ORMRecommendation, QueryOptimizerMiddleware,
│                                             NplusOneDetector, SelectRelatedDetector,
│                                             DRFSerializerDetector, QueryScorer,
│                                             QueryStore, RequestRecord,
│                                             RegressionDetector, SARIFReporter, install()
├── _internal/bootstrap.py      → idempotent Django hook registration
├── collectors/query_collector.py → CapturedQuery + QueryCollector (execute_wrapper)
├── middleware/query_collector_middleware.py → per-request collector, sets endpoint
├── analyzers/query_analyzer.py   → slow_query + duplicate_query detectors
├── detectors/
│   ├── base.py                   → BaseDetector protocol
│   ├── n_plus_one.py             → NplusOneDetector
│   ├── select_related.py         → SelectRelatedDetector
│   └── drf_serializer.py         → DRFSerializerDetector (Phase 2b)
├── recommendations/base.py       → ORMRecommendation frozen dataclass + Severity enum
├── scoring/query_scorer.py       → QueryScorer — 0-100 health score + letter grade
├── regression/detector.py        → RegressionDetector — baseline compare + JSON persist
├── reporting/sarif.py            → SARIFReporter — SARIF 2.1 output for VS Code / CI
├── store.py                      → QueryStore + RequestRecord — in-memory request history
├── admin/                        → Django Admin dashboard
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
│   ├── test_admin.py
│   ├── test_init.py                    # public API surface smoke test
│   ├── test_middleware.py
│   ├── test_n_plus_one_detector.py
│   ├── test_drf_serializer_detector.py # DRFSerializerDetector unit tests
│   ├── test_pytest_plugin.py
│   ├── test_query_analyzer.py          # QueryAnalyzer detector unit tests
│   ├── test_query_collector.py         # QueryCollector unit tests
│   ├── test_query_scorer.py
│   ├── test_recommendations.py         # ORMRecommendation + Severity unit tests
│   ├── test_regression_detector.py
│   ├── test_sarif_reporter.py
│   ├── test_select_related_detector.py
│   └── test_store.py
└── integration/                        # Phase 4+ (empty)
```

Coverage threshold: **85%** (enforced by `pytest-cov` with `fail_under = 85`).

---

## Adding a New Detector

1. Create `src/django_query_optimizer/detectors/<name>.py` implementing `detect(queries) -> list[ORMRecommendation]`.
2. Export the class from `__init__.py` and add it to `__all__`.
3. Write a matching test class in `tests/unit/test_<name>_detector.py`.
4. Update the detector table in `README.md` and this file.
5. Use an existing `Severity` level or add to the enum if justified.

---

## Conventions

- Public API exports live in `__init__.py.__all__` — nothing else is considered stable.
- No breaking changes without a major version bump.
- All type annotations must pass `mypy --strict`.
- Commit identity: `user.name=chrysa`, `user.email=greau.anthony+chrysa@gmail.com`.
