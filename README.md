# django-query-optimizer

![Python](https://img.shields.io/badge/python-3.14%2B-blue)
![Django](https://img.shields.io/badge/django-4.2%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Status](https://img.shields.io/badge/status-pre--alpha-orange)

Intelligent ORM analysis and optimization platform for Django.

Detects N+1 queries, duplicate queries, slow queries, missing indexes, and more — directly in
Django Admin, your test suite, and VS Code.

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Public API](#public-api)
   - [QueryCollector](#querycollector)
   - [QueryAnalyzer](#queryanalyzer)
   - [ORMRecommendation & Severity](#ormrecommendation--severity)
   - [install()](#install)
6. [pytest Integration](#pytest-integration)
7. [Configuration](#configuration)
8. [Development](#development)
9. [Contributing](#contributing)
10. [License](#license)

---

## Features

| Phase | Feature | Status |
|---|---|---|
| 1a — Core | SQL collection (`QueryCollector`), `QueryAnalyzer`, slow query & duplicate detectors | ✅ Done |
| 1b — HTTP Middleware | `QueryOptimizerMiddleware` — per-request collector, sets `endpoint` / `python_file` / `python_line` | ✅ Done |
| 1c — Admin | Django Admin dashboard (session list, top slow queries) | ✅ Done |
| 2a — N+1 detector | `NplusOneDetector` — groups repeated SQL patterns by call-site, severity escalation | ✅ Done |
| 2b — DRF detector | `DRFSerializerDetector` — N+1 patterns triggered by DRF serializer/relation/field code | ✅ Done |
| 2c — FK detector | `SelectRelatedDetector` — single-row FK lookup repetitions | ✅ Done |
| 2d — Scoring | `QueryScorer` — 0-100 health score + letter grade (A–F) | ✅ Done |
| 3 — Testing | `SARIFReporter`, `RegressionDetector`, `--query-analysis` pytest flag | ✅ Done |
| 4 — VS Code | Inline diagnostics (SARIF), realtime warnings | 🚧 In Progress |
| 5 — Multi Framework | FastAPI, SQLAlchemy, Prisma | Planned |

---

## Architecture

```
src/django_query_optimizer/
├── __init__.py                    # Public API
├── py.typed                       # PEP 561 marker
├── _internal/
│   ├── bootstrap.py               # One-time registration hook (idempotent)
│   └── version.py                 # __version__ constant
├── collectors/
│   └── query_collector.py         # CapturedQuery dataclass + QueryCollector context-manager
├── middleware/
│   └── query_collector_middleware.py  # QueryOptimizerMiddleware — per-request collector
├── analyzers/
│   └── query_analyzer.py          # QueryAnalyzer — slow query & duplicate detectors
├── detectors/
│   ├── base.py                    # BaseDetector protocol
│   ├── n_plus_one.py              # NplusOneDetector — repeated SQL pattern detection
│   ├── select_related.py          # SelectRelatedDetector — FK lookup repetitions
│   └── drf_serializer.py          # DRFSerializerDetector — DRF serializer N+1 patterns
├── recommendations/
│   └── base.py                    # ORMRecommendation frozen dataclass + Severity enum
├── scoring/
│   └── query_scorer.py            # QueryScorer — 0-100 health score + letter grade
├── regression/
│   └── detector.py                # RegressionDetector — baseline compare + JSON persist
├── reporting/
│   └── sarif.py                   # SARIFReporter — SARIF 2.1 output for VS Code / CI
├── store.py                       # QueryStore + RequestRecord — in-memory request history
├── admin/                         # Django Admin dashboard
└── testing/
    └── pytest_plugin.py           # pytest entry-point: --query-analysis flag + fixture
```

**Data flow:**

```
Django ORM execute_wrapper
        │
        ▼
  QueryCollector          ← captures CapturedQuery (sql, duration_ms, stack_trace)
        │
        ▼
  QueryAnalyzer           ← runs detectors over the collected queries
        │
        ▼
  [ORMRecommendation]     ← sorted by Severity (CRITICAL → HIGH → MEDIUM → LOW → INFO)
```

---

## Installation

```bash
pip install django-query-optimizer
```

**Optional extras:**

| Extra | Installs |
|---|---|
| `postgres` | `psycopg2-binary` — PostgreSQL driver |
| `drf` | `djangorestframework` — DRF serializer analysis (Phase 2) |
| `realtime` | `channels` + `daphne` — WebSocket live dashboard (Phase 4) |

```bash
pip install "django-query-optimizer[postgres,drf]"
```

Activate in your **development** settings only:

```python
# settings/local.py
import django_query_optimizer
django_query_optimizer.install()

# Add the middleware (must come after SessionMiddleware)
MIDDLEWARE = [
    ...
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_query_optimizer.middleware.query_collector_middleware.QueryOptimizerMiddleware",
    ...
]
```

> **Warning:** Do not add `install()` or the middleware to production settings. Both add
> overhead to every database query.

### Admin dashboard (optional)

To expose the **Query Optimizer** dashboard under Django Admin, add the app to
`INSTALLED_APPS` and apply migrations:

```python
INSTALLED_APPS = [
    ...
    "django.contrib.admin",
    "django_query_optimizer",
]
```

```bash
python manage.py migrate django_query_optimizer
```

The shipped migration only registers an **unmanaged** `QueryLog` proxy model
(`managed = False`, no table created) so that the admin section and its
`ContentType` / `Permission` rows exist. The dashboard reads the in-process
`QueryStore`, not the database.

---

## Quick Start

### Context-manager (one-off analysis)

```python
from django_query_optimizer import QueryCollector, QueryAnalyzer

with QueryCollector() as collector:
    list(Order.objects.all())           # run any ORM operations here
    list(OrderItem.objects.all())

analyzer = QueryAnalyzer(collector.queries)
for rec in analyzer.analyze():
    print(f"[{rec.severity.value.upper()}] {rec.message}")
    print(f"  → {rec.suggestion}")
    if rec.python_file:
        print(f"  @ {rec.python_file}:{rec.python_line}")
```

### Example output

```
[HIGH] Query took 142.3 ms (threshold: 100 ms)
  → Consider adding a database index, using only() / values(), or caching the result.
[MEDIUM] Query executed 4 times: SELECT "shop_order"."id" FROM "shop_order" WHERE ...
  → Cache the queryset result, use select_related() / prefetch_related(), or restructure the loop.
```

---

## Public API

### QueryCollector

```python
from django_query_optimizer import QueryCollector
```

A thread-safe context-manager that hooks into Django's `execute_wrapper` to record every SQL
query executed while the collector is active.

| Attribute | Type | Description |
|---|---|---|
| `queries` | `list[CapturedQuery]` | All queries captured in this session |
| `count` | `int` (property) | Number of captured queries |

**`CapturedQuery` fields:**

| Field | Type | Description |
|---|---|---|
| `sql` | `str` | Raw SQL string as sent to the database |
| `duration_ms` | `float` | Execution time in milliseconds |
| `stack_trace` | `list[str]` | Python call-stack at query time |
| `endpoint` | `str` | HTTP endpoint (populated by middleware, optional) |
| `python_file` | `str` | Source file that triggered the query (best-effort) |
| `python_line` | `int` | Line number in `python_file` (0 = unknown) |

```python
with QueryCollector() as col:
    MyModel.objects.filter(active=True)

print(col.count)          # number of queries
print(col.queries[0].sql) # raw SQL of the first query
```

---

### QueryAnalyzer

```python
from django_query_optimizer import QueryAnalyzer
```

Runs a set of built-in detectors over a `list[CapturedQuery]` and returns
`list[ORMRecommendation]` sorted from most to least severe.

```python
analyzer = QueryAnalyzer(collector.queries)
recommendations = analyzer.analyze()
```

**Built-in detectors:**

| Detector | Class | Severity | Trigger |
|---|---|---|---|
| `slow_query` | `QueryAnalyzer` | HIGH | `duration_ms >= 100.0` ms |
| `duplicate_query` | `QueryAnalyzer` | MEDIUM | Same SQL executed ≥ 2 times |
| `n_plus_one` | `NplusOneDetector` | MEDIUM / HIGH / CRITICAL | Same SQL pattern from same call-site |
| `missing_select_related` | `SelectRelatedDetector` | MEDIUM / HIGH | FK lookup repeated from same call-site |
| `drf_n_plus_one` | `DRFSerializerDetector` | MEDIUM / HIGH | Repeated SQL originating from DRF serializer code |

---

### ORMRecommendation & Severity

```python
from django_query_optimizer import ORMRecommendation
from django_query_optimizer.recommendations.base import Severity
```

`ORMRecommendation` is a **frozen dataclass** (hashable, immutable):

| Field | Type | Description |
|---|---|---|
| `issue_type` | `str` | Short identifier, e.g. `"slow_query"`, `"duplicate_query"` |
| `severity` | `Severity` | How urgent the fix is |
| `message` | `str` | Human-readable problem description |
| `suggestion` | `str` | Concrete fix (ORM method to apply) |
| `python_file` | `str` | Origin file (best-effort, empty if unknown) |
| `python_line` | `int` | Line number (0 = unknown) |

`Severity` values, from most to least urgent:

```python
Severity.CRITICAL   # "critical"
Severity.HIGH       # "high"
Severity.MEDIUM     # "medium"
Severity.LOW        # "low"
Severity.INFO       # "info"
```

Recommendations support `<` comparison and are sortable by severity:

```python
recs = sorted(analyzer.analyze())  # CRITICAL first
```

---

### QueryOptimizerMiddleware

```python
from django_query_optimizer import QueryOptimizerMiddleware
# or referenced by path in MIDDLEWARE:
# "django_query_optimizer.middleware.query_collector_middleware.QueryOptimizerMiddleware"
```

Django WSGI/ASGI middleware that wraps each HTTP request in a `QueryCollector`.
After the response is built it populates `endpoint` (request path) on every
captured query and attaches the collector to `request.query_collector` for
downstream access (e.g. the Admin dashboard).

```python
def my_view(request):
    # The middleware has already started collecting — just use the attached collector.
    qs = MyModel.objects.all()
    response = render(request, "list.html", {"objects": qs})
    # After the view, middleware sets query.endpoint = "/my-path/" on all queries.
    return response
```

---

### install()

```python
import django_query_optimizer
django_query_optimizer.install()
```

Registers the global Django `execute_wrapper` used by `QueryCollector.register()`.
Idempotent — safe to call multiple times. Designed for `settings/local.py` or
`AppConfig.ready()`.

---

## pytest Integration

### Flag: `--query-analysis`

Enable ORM analysis on every test run:

```bash
pytest --query-analysis
```

### Fixture: `query_collector`

Use the built-in fixture to assert on query counts or inspect recommendations in any test:

```python
def test_order_list_api(client, query_collector):
    response = client.get("/api/orders/")
    assert response.status_code == 200
    # Fail if the view issues more than 3 queries
    assert query_collector.count <= 3

def test_no_slow_queries(client, query_collector):
    from django_query_optimizer import QueryAnalyzer
    from django_query_optimizer.recommendations.base import Severity

    client.get("/api/orders/")
    analyzer = QueryAnalyzer(query_collector.queries)
    high_severity = [r for r in analyzer.analyze() if r.severity == Severity.HIGH]
    assert high_severity == [], high_severity
```

The `query_collector` fixture is **function-scoped**: each test gets a fresh collector.

### Flag: `--sarif-output FILE` _(Phase 4 — in progress)_

Write a [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
report at the end of the test session. Requires `--query-analysis`.

```bash
pytest --query-analysis --sarif-output query-results.sarif
```

All findings accumulated across the entire session are serialised via `SARIFReporter`
into the specified file. Parent directories are created automatically.

The report can be consumed by the
[django-query-optimizer VS Code extension](https://github.com/chrysa/django-query-optimizer-vscode),
which surfaces findings as inline squiggles and Problems panel entries.

**CI integration example** (write SARIF, upload as GitHub Actions artifact):

```yaml
- name: Run tests with ORM analysis
  run: pytest --query-analysis --sarif-output reports/query-results.sarif

- name: Upload SARIF
  uses: actions/upload-artifact@v4
  if: always()
  with:
    name: sarif-report
    path: reports/query-results.sarif
```

---

## Configuration

Threshold constants live in `analyzers/query_analyzer.py` and can be overridden at import time:

```python
import django_query_optimizer.analyzers.query_analyzer as _qa

_qa.SLOW_QUERY_THRESHOLD_MS = 50.0   # tighten the slow-query limit
_qa.DUPLICATE_MIN_COUNT = 3          # only warn on 3+ duplicates
```

> A proper settings-based configuration system is planned for Phase 2.

---

## Development

**Prerequisites:** Docker + Docker Compose

```bash
make install-dev    # install package + dev extras locally (optional)
make docker-test    # build image and run full test suite with coverage
make lint           # ruff check (via Docker)
make typecheck      # mypy --strict (via Docker)
make lint-all       # lint + typecheck
make pre-commit     # run all pre-commit hooks on every file
```

**Coverage threshold:** 85% (enforced by pytest-cov — CI will fail below this).

**Adding a new detector:**

1. Implement a private `_detect_<name>` method in `QueryAnalyzer`.
2. Call it from `analyze()` and extend the return list.
3. Add a matching unit-test class in `tests/unit/test_query_analyzer.py`.
4. Update the detector table in this README.

---

## Contributing

1. Fork the repo and create a branch: `feat/<issue-id>-short-desc`.
2. Write tests **before** implementing (TDD).
3. Ensure `make docker-test` passes with coverage ≥ 85%.
4. Open a PR — squash merge once CI is green and 1 approval received.

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): description` (imperative, lowercase, no trailing period).

---

## License

MIT — see [LICENSE](LICENSE).
