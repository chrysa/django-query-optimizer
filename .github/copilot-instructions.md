# django-query-optimizer — GitHub Copilot Instructions

## Purpose
Django library for automatic query optimization: detects N+1 queries, suggests prefetch/select_related,
and provides query plan analysis. Pre-alpha — API still evolving.

## Stack
- **Language**: Python 3.14+
- **Framework**: Django 4.2+
- **Testing**: pytest + pytest-django
- **Linting**: ruff
- **Type checking**: mypy (strict)
- **Build**: pyproject.toml (setuptools)
- **Docker**: multi-stage Dockerfile for isolated test environments

## Project Structure
```
django_query_optimizer/   # Library source package
  analyzers/              # Query analysis logic
  middleware/             # Django middleware integration
  decorators/             # @optimize_queryset and similar
tests/                    # pytest test suite
docs/                     # Architecture decisions, API reference
pyproject.toml            # Package config + dev dependencies
```

## Development Rules
- All tests must run via `make docker-test` — never directly with `pytest` on host.
- All linting via `make lint` (delegates to pre-commit / ruff).
- Public API changes require DECISIONS.md entry + version bump.
- Minimum test coverage: 85%.
- No Django models or views in the library itself — test models go in `tests/`.
- Type hints required on all public functions.

## Makefile targets
See `make help` for all available targets.
