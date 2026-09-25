# Testing — django-query-optimizer

> Facts from `tests/`, `pyproject.toml`, `Makefile`, `docker-compose.yml`, CLAUDE.md.
> Commands were NOT executed for this doc (documentation-only task); they are transcribed
> from repository config and marked accordingly.

## How tests are run (chrysa containers-only policy)

Never run pytest / ruff / mypy on the host. Use `make` targets (execute in Docker):

```bash
make test          # tests with coverage (Docker)          FACT (Makefile / ARCHITECTURE.md)
make test-fast     # tests without coverage (Docker)        FACT
make docker-test   # build + run tests (CI target)          FACT
make ci            # lint + typecheck + test                FACT
make lint          # ruff check                             FACT
make typecheck     # mypy                                   FACT
```

A `.claude/hookify.warn-host-test-lint.local.md` hook warns when tests/lint are run on the host.

> Self-plugin caveat: this package registers a `pytest11` entry-point (`--query-analysis`).
> If its own suite is invoked in a context where the plugin misbehaves, disable it with
> `-p no:query_optimizer`. INFERENCE (from sibling-repo memory; not reproduced here).

## Coverage gate

- **≥ 85%**, enforced by pytest-cov `fail_under = 85`; CI fails below. FACT (README, CLAUDE.md, `pyproject.toml`; `coverage.xml` present, `branch = true`).

## Test layout (FACT — from `tests/`)

| File | Target under test |
|---|---|
| `tests/conftest.py`, `tests/settings.py`, `tests/settings_mypy.py` | Django test settings / fixtures |
| `unit/test_query_collector.py` | `QueryCollector` (`execute_wrapper` capture) |
| `unit/test_query_analyzer.py` | `QueryAnalyzer` (slow/duplicate) |
| `unit/test_n_plus_one_detector.py` | `NplusOneDetector` |
| `unit/test_drf_serializer_detector.py` | `DRFSerializerDetector` |
| `unit/test_select_related_detector.py` | `SelectRelatedDetector` |
| `unit/test_recommendations.py` | `ORMRecommendation` + `Severity` |
| `unit/test_query_scorer.py` | `QueryScorer` / `QueryScore` |
| `unit/test_middleware.py` | `QueryOptimizerMiddleware` |
| `unit/test_store.py` | `QueryStore` / `RequestRecord` |
| `unit/test_admin.py` | Admin dashboard |
| `unit/test_pytest_plugin.py` | pytest plugin + `query_collector` fixture |
| `unit/test_sarif_reporter.py` | `SARIFReporter` (SARIF 2.1) |
| `unit/test_regression_detector.py` | `RegressionDetector` |
| `unit/test_init.py` | Public API surface smoke test |
| `integration/test_packaging.py` | Wheel/sdist ships data files (template, `py.typed`) |

CLAUDE.md notes `integration/` as "Phase 4+ (empty)"; the repo now contains `test_packaging.py` there — CLAUDE.md is slightly stale on this point (see REVIEW).

## Using the fixture in downstream projects (FACT — README)

```python
def test_endpoint(client, query_collector):
    response = client.get("/orders/")
    assert response.status_code == 200
    assert query_collector.count <= 3           # fail on query-count budget
    # or assert on severity of recommendations
```

## Not verified here

- Actual pass/fail state, coverage %, and mypy-strict green status were not executed (docs-only). UNKNOWN as of this pass; `coverage.xml`/`.coverage` artifacts exist but were not parsed as authoritative.
