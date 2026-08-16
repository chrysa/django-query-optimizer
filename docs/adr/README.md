# Architecture Decision Records

**Role.** Versioned log of structural decisions for `django-query-optimizer`.

Series prefix: `ADR-NNNN`. One decision per file, append-only. A decision is never
edited in place once `Accepted`; it is superseded by a new ADR that links back.

## Structure

| Path | Purpose |
| --- | --- |
| `README.md` | This index + conventions. |
| `ADR-0001-execute-wrapper-collection.md` | Why query capture uses `execute_wrapper`. |

## Should contain

- One ADR per structural decision (new external dep, public-API break, data-model
  change, provider choice, or a chrysa pillar exception).

## Should NOT contain

- Task notes, sprint logs, or how-to docs — those go in `docs/` or the tracker.

## Rules

- Every chrysa ADR carries the three refutable fields: **Fatal hypothesis**,
  **Kill-test**, **Validation gate** (see root `CLAUDE.md` → Governance).
- `Killed` is a valid status. Scaffold new records with `/adr-new`.

## Index

| ADR | Title | Status |
| --- | --- | --- |
| 0001 | execute_wrapper query collection | Accepted |
