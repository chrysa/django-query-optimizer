# Decisions — django-query-optimizer

> ADR-style record of load-bearing decisions. The canonical ADR store is `docs/adr/`
> (`docs/adr/README.md` + `ADR-0001-execute-wrapper-collection.md`). This file summarizes
> and indexes them; unknown context is tagged UNKNOWN. Do not duplicate — see `docs/adr/`.

## Index

| ID | Decision | Source | Status |
|---|---|---|---|
| ADR-0001 | Capture queries via `connection.execute_wrappers`. | `docs/adr/ADR-0001-execute-wrapper-collection.md` | Accepted; validation gate OPEN |
| DEC-002 | `ORMRecommendation` is a frozen dataclass (hashable, sortable, immutable). | CLAUDE.md Key Design Decisions | Accepted (INFERENCE: no ADR file) |
| DEC-003 | `Severity` is a `StrEnum` so `rec.severity == "high"` works without importing the enum. | CLAUDE.md | Accepted (INFERENCE) |
| DEC-004 | Thresholds are module-level constants (`SLOW_QUERY_THRESHOLD_MS`, `DUPLICATE_MIN_COUNT`) so tests can override them. | CLAUDE.md; README §Configuration | Accepted |
| DEC-005 | pytest plugin registered via `entry-points` for zero-config activation after install. | CLAUDE.md; `pyproject.toml` | Accepted |
| DEC-006 | Admin dashboard uses an **unmanaged** `QueryLog` proxy model (`managed=False`, no table). | README §Admin; `migrations/0001_initial.py` | Accepted |
| DEC-007 | Version centralized in `_internal/version.py` via `importlib.metadata` to avoid an import cycle with the package root. | `_internal/version.py` docstring | Accepted |
| DEC-008 | SARIF 2.1 chosen as the interchange format to CI and the VS Code extension. | `reporting/sarif.py`; README | Accepted |

## ADR-0001 essentials (see file for full text)

- **Chosen**: `connection.execute_wrappers`. Rejected alternatives listed in the ADR (UNKNOWN which — file lists candidates 1–n).
- **Rationale**: works in tests with no HTTP and no `DEBUG=True`, unlike `connection.queries` (gated on DEBUG, unbounded memory).
- **Cost**: a full Python stack is extracted per query (`traceback.extract_stack`) to resolve the originating user frame — the main runtime cost.
- **Fatal hypothesis / kill-test**: per-query stack overhead must add < 15% wall-clock on a 500-query view in CI.
- **Validation gate**: benchmark test "Not yet implemented — gate open" per the ADR. UNKNOWN if satisfied since (a `.benchmarks/` dir exists at root but was not inspected as source).

## Decisions needing an ADR (proposal)

- PROPOSAL: promote DEC-002…DEC-008 to numbered ADR files under `docs/adr/` for parity with the ADR-per-decision convention in `docs/adr/README.md`.
