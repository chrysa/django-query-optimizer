# Requirements — django-query-optimizer

> Generated from repository evidence (README.md, CLAUDE.md, source, pyproject.toml). Each
> requirement is tagged FACT (verifiable in the repo), INFERENCE (deduced), or UNKNOWN.
> A requirement is marked IMPLEMENTED only when a concrete code/test artifact is cited.

## Functional requirements

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| REQ-FUN-001 | Capture every SQL query the Django ORM issues, without requiring an HTTP layer or `DEBUG=True`. | `collectors/query_collector.py` (`QueryCollector`, `execute_wrapper`); ADR-0001. FACT | IMPLEMENTED |
| REQ-FUN-002 | Analyze collected queries for slow queries and duplicate queries. | `analyzers/query_analyzer.py` (`QueryAnalyzer`); `tests/unit/test_query_analyzer.py`. FACT | IMPLEMENTED |
| REQ-FUN-003 | Detect N+1 query patterns grouped by call-site with severity escalation. | `detectors/n_plus_one.py` (`NplusOneDetector`); `tests/unit/test_n_plus_one_detector.py`. FACT | IMPLEMENTED |
| REQ-FUN-004 | Detect N+1 caused by DRF serializer/relation/field code. | `detectors/drf_serializer.py` (`DRFSerializerDetector`); `tests/unit/test_drf_serializer_detector.py`. FACT | IMPLEMENTED |
| REQ-FUN-005 | Detect repeated FK lookups that `select_related()` would collapse. | `detectors/select_related.py` (`SelectRelatedDetector`); `tests/unit/test_select_related_detector.py`. FACT | IMPLEMENTED |
| REQ-FUN-006 | Produce `ORMRecommendation` objects, sortable by `Severity` (CRITICAL→INFO). | `recommendations/base.py`; `tests/unit/test_recommendations.py`. FACT | IMPLEMENTED |
| REQ-FUN-007 | Score a request's query health as a 0-100 score plus letter grade A-F. | `scoring/query_scorer.py` (`QueryScorer`, `QueryScore`); `tests/unit/test_query_scorer.py`. FACT | IMPLEMENTED |
| REQ-FUN-008 | Capture per-request query activity via HTTP middleware. | `middleware/query_collector_middleware.py` (`QueryOptimizerMiddleware`); `tests/unit/test_middleware.py`. FACT | IMPLEMENTED |
| REQ-FUN-009 | Keep an in-memory history of request records. | `store.py` (`QueryStore`, `RequestRecord`); `tests/unit/test_store.py`. FACT | IMPLEMENTED |
| REQ-FUN-010 | Expose a dashboard in Django Admin over an unmanaged `QueryLog` proxy model (no table created). | `admin/`, `migrations/0001_initial.py`; `tests/unit/test_admin.py`; README §Admin. FACT | IMPLEMENTED |
| REQ-FUN-011 | Provide a pytest plugin (`--query-analysis` flag + `query_collector` fixture) via entry-point. | `testing/pytest_plugin.py`; `[project.entry-points."pytest11"]`; `tests/unit/test_pytest_plugin.py`. FACT | IMPLEMENTED |
| REQ-FUN-012 | Emit SARIF 2.1 output for CI / the VS Code extension. | `reporting/sarif.py` (`SARIFReporter`); `tests/unit/test_sarif_reporter.py`. FACT | IMPLEMENTED |
| REQ-FUN-013 | Detect regressions by comparing against a persisted JSON baseline. | `regression/detector.py` (`RegressionDetector`, `RegressionResult`); `tests/unit/test_regression_detector.py`. FACT | IMPLEMENTED |
| REQ-FUN-014 | Idempotent one-call activation `install()` from `AppConfig.ready()` or dev settings. | `__init__.py` `install()` → `_internal/bootstrap.py`; `tests/unit/test_init.py`. FACT | IMPLEMENTED |
| REQ-FUN-015 | VS Code inline diagnostics / realtime warnings consuming SARIF. | README Phase 4 "In Progress"; external repo `chrysa/django-query-optimizer-vscode`. FACT (out of this repo's scope) | NOT IMPLEMENTED (here) |
| REQ-FUN-016 | Multi-framework support (FastAPI, SQLAlchemy, Prisma). | README Phase 5 "Planned". FACT | PLANNED |

## Non-functional requirements

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| REQ-NFR-001 | Public API surface is limited to `__init__.__all__`; nothing else is stable. | CLAUDE.md Conventions; `__init__.py`. FACT | IMPLEMENTED |
| REQ-NFR-002 | All type annotations pass mypy (strict configured). | `pyproject.toml [tool.mypy]`; CLAUDE.md. FACT | IMPLEMENTED (INFERENCE on green state) |
| REQ-NFR-003 | Test coverage ≥ 85%, enforced by pytest-cov `fail_under`. | README §Coverage; CLAUDE.md; `pyproject.toml`. FACT | IMPLEMENTED |
| REQ-NFR-004 | Collector overhead stays usable in a real request path (< 15% wall-clock on 500-query view). | ADR-0001 Kill-test. FACT (gate) | NOT VERIFIED — benchmark gate OPEN |
| REQ-NFR-005 | `install()` / middleware must not be added to production settings. | README Warning; CLAUDE.md. FACT | DOCUMENTED |
| REQ-NFR-006 | Package ships non-Python data files (admin template, `py.typed`). | `pyproject.toml [tool.setuptools]` comment + globs; `tests/integration/test_packaging.py`. FACT | IMPLEMENTED |

## Open / unverifiable

- REQ-NFR-004 benchmark: ADR-0001 states the validation gate is "Not yet implemented — gate open". UNKNOWN whether a benchmark test now exists despite the `.benchmarks/` directory at root.
