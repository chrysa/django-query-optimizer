# Roadmap — django-query-optimizer

> Transcribed from README §Roadmap and CLAUDE.md §Project State. Status tags are as declared
> in the repo (FACT). Current version **0.1.0**, pre-alpha, unreleased on PyPI.

| Phase | Scope | Status |
|---|---|---|
| 1a | Core: collector, analyzer, slow/duplicate detectors | ✅ Done |
| 1b | HTTP middleware (`QueryOptimizerMiddleware`) | ✅ Done |
| 1c | Admin dashboard | ✅ Done |
| 2a | N+1 detector (`NplusOneDetector`) | ✅ Done |
| 2b | DRF serializer N+1 detector (`DRFSerializerDetector`) | ✅ Done |
| 2c | FK detector (`SelectRelatedDetector`) | ✅ Done |
| 2d | Query scoring (`QueryScorer`) | ✅ Done |
| 3 | pytest SARIF report + `RegressionDetector` | ✅ Done |
| 4 | VS Code extension (reads SARIF) — active dev in `chrysa/django-query-optimizer-vscode` | 🚧 In Progress |
| 5 | Multi-framework (FastAPI, SQLAlchemy, Prisma) | Planned |

## Known open items (FACT)

- **ADR-0001 validation gate OPEN**: the < 15% overhead benchmark test is declared "not yet
  implemented" in the ADR. Until closed, the collector is not validated for production/middleware
  hot paths.
- Phase 4 (VS Code) work lives in the external `-vscode` repo; the SARIF prerequisite
  (`--sarif-output`, PR #22) shipped here.

## Cross-repo lineage (per task brief — verify before relying)

- `fastapi-query-optimizer` is described as the FastAPI port of this Django original. Not evidenced
  inside this repo. INFERENCE.
- `django-query-optimizer-vscode` consumes this repo's SARIF. FACT (README link).
