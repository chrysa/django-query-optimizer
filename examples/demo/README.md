# django-query-optimizer — runnable demo

A minimal Django project that demonstrates the optimizer catching an N+1 query
pattern, both at runtime (admin dashboard) and in tests (pytest fixtures).

## What it shows

- `django_query_optimizer.install()` + `QueryOptimizerMiddleware` wired into
  development settings (`demo_project/settings.py`).
- A `catalog` app with an N+1-prone relation (`Book` → `Author`).
- Two views: `/books/naive/` (1 + N queries) and `/books/optimized/`
  (`select_related`, a single query).
- The **Query Optimizer** admin dashboard aggregating per-request query stats.
- pytest fixture (`assert_query_health`) failing a test when an N+1 appears,
  in `tests/test_query_budget.py`.

## Run it

From the repository root, install the package with dev extras (use Docker or a
virtualenv — never the system Python):

```bash
pip install -e ".[dev]"
```

Then, from this directory (`examples/demo/`):

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser   # to log into the admin
python manage.py runserver
```

Open:

1. <http://127.0.0.1:8000/books/naive/> — renders the list (runs 1 + N queries).
2. <http://127.0.0.1:8000/books/optimized/> — same data, one query.
3. <http://127.0.0.1:8000/admin/django_query_optimizer/querylog/> — the
   dashboard. Compare the query counts for the two endpoints; the naive one
   carries an N+1 recommendation.

## Run the pytest demo

```bash
pytest
```

`test_optimized_listing_is_healthy` passes; `test_naive_listing_is_unhealthy`
proves the optimizer flags the naive view's N+1.
