# Glossary — django-query-optimizer

> Terms and public symbols, grounded in `src/` and README. Public API = `__init__.__all__`.

## Public API symbols (FACT — `__init__.py`)

| Symbol | Meaning |
|---|---|
| `QueryCollector` | Thread-safe context manager hooking `execute_wrapper` to record every SQL query executed while active. |
| `QueryAnalyzer` | Runs slow-query and duplicate-query analysis over collected queries. |
| `NplusOneDetector` | Detects N+1 patterns grouped by call-site with severity escalation. |
| `SelectRelatedDetector` | Detects repeated FK lookups a `select_related()` would collapse. |
| `DRFSerializerDetector` | Detects N+1 originating in DRF serializer/relation/field code. |
| `QueryScorer` / `QueryScore` | Computes a 0-100 health score and letter grade A-F for a request's queries. |
| `ORMRecommendation` | Frozen, sortable dataclass: one optimization recommendation. |
| `Severity` | `StrEnum` — CRITICAL / HIGH / MEDIUM / LOW / INFO. |
| `QueryOptimizerMiddleware` | Per-request Django middleware wrapping a collector; sets the endpoint. |
| `QueryStore` / `RequestRecord` | In-memory history store and per-request snapshot. |
| `RegressionDetector` / `RegressionResult` | Compare current run against a persisted JSON baseline. |
| `SARIFReporter` | Emits SARIF 2.1 for CI / the VS Code extension. |
| `install()` | Idempotent activation of the hooks/middleware (dev only). |
| `__version__` | Package version from `importlib.metadata` (= `pyproject` version). |

## Domain terms

| Term | Meaning |
|---|---|
| N+1 query | One query per row of a prior result set instead of a single joined/prefetched query. |
| Duplicate query | Identical SQL executed multiple times in one request/test (threshold `DUPLICATE_MIN_COUNT`). |
| Slow query | Query exceeding `SLOW_QUERY_THRESHOLD_MS`. |
| `execute_wrapper` | Django `connection.execute_wrappers` hook used to intercept SQL (ADR-0001). |
| SARIF | Static Analysis Results Interchange Format 2.1 — the CI/VS Code output format. |
| Unmanaged proxy model | `QueryLog` with `managed=False`: admin section without creating a DB table. |
| Baseline | JSON snapshot used by `RegressionDetector` to detect regressions. |

## Related repositories (FACT — README / CLAUDE.md)

| Repo | Relationship |
|---|---|
| `chrysa/django-query-optimizer-vscode` | VS Code extension consuming this repo's SARIF output (Phase 4). |
| `fastapi-query-optimizer` | Port of this Django original to FastAPI (per task brief; not referenced in this repo's files — INFERENCE/UNKNOWN, see REVIEW). |
