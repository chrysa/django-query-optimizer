# django-query-optimizer

Intelligent ORM analysis and optimization platform for Django.

Detects N+1 queries, duplicate queries, slow queries, missing indexes, and more — directly in Django Admin, your test suite, and VS Code.

## Features (roadmap)

| Phase | Feature | Status |
|---|---|---|
| 1 — MVP | SQL collection, slow query detection, duplicate detection, Admin dashboard | In progress |
| 2 — ORM Intelligence | N+1 detection, select_related suggestions, DRF serializer analysis, query scoring | Planned |
| 3 — Testing | pytest plugin `--query-analysis`, regression detection, CI integration | Planned |
| 4 — VS Code | Inline diagnostics, quick fixes, realtime warnings | Planned |
| 5 — Multi Framework | FastAPI, SQLAlchemy, Prisma | Planned |

## Installation

```bash
pip install django-query-optimizer
```

Add to your development settings:

```python
# settings/local.py
import django_query_optimizer
django_query_optimizer.install()
```

## Quick Start

```python
from django_query_optimizer import QueryCollector, QueryAnalyzer

with QueryCollector() as collector:
    list(Order.objects.all())

analyzer = QueryAnalyzer(collector.queries)
for rec in analyzer.analyze():
    print(f"[{rec.severity.value}] {rec.message}")
    print(f"  → {rec.suggestion}")
```

## pytest Integration

```bash
pytest --query-analysis
```

Or use the fixture:

```python
def test_my_view(query_collector):
    response = client.get("/api/orders/")
    assert query_collector.count < 5
```

## Development

```bash
make install-dev   # install with dev extras
make docker-test   # run full test suite via Docker
make docker-lint   # ruff + mypy via Docker
```

## License

MIT — see [LICENSE](LICENSE).
