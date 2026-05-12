# django-query-optimizer — Agent Instructions

Read [`CLAUDE.md`](../CLAUDE.md) and [`shared-standards/`](../shared-standards/) first.

## Purpose
Python library that provides real-time ORM query analysis, N+1 detection,
and optimization recommendations for Django applications.

## Architecture
```
src/django_query_optimizer/
├── __init__.py                     # public API
├── py.typed                        # PEP 561
├── _internal/
│   ├── bootstrap.py                # one-time registration (idempotent)
│   └── version.py                  # __version__ constant
├── collectors/query_collector.py   # CapturedQuery + QueryCollector
├── analyzers/query_analyzer.py     # QueryAnalyzer — slow + duplicate detectors
├── detectors/                      # Phase 2 — N+1, select_related, DRF
├── recommendations/base.py         # ORMRecommendation + Severity
├── admin/                          # Phase 1 — Django Admin dashboard
└── testing/pytest_plugin.py        # pytest entry point
```

## Commands
```bash
make docker-test    # run full test suite via Docker
make docker-lint    # ruff + mypy via Docker
make install-dev    # local dev install
```

## Conventions
- Coverage threshold: 85%
- Public API: documented in `__init__.py.__all__`
- No breaking changes without major version bump
- All detectors live in `analyzers/` or `detectors/`
- New issue type → add to `Severity` enum if needed + unit test
