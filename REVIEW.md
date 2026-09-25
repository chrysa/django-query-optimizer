# Documentation Review — django-query-optimizer

> Output of a documentation-only pass (2026-09-25). No source/tests/config changed. This file
> records contradictions, stale docs, gaps, and documentation debt for the owner.

## Contradictions found

| # | Contradiction | Evidence | Resolution |
|---|---|---|---|
| C-1 | Django version: README badge "django 4.2+" and classifiers `Django :: 4.2/5.0/5.1` vs runtime dependency `django>=6.0.7`. | `README.md` badge; `pyproject.toml` classifiers L24-35 & `dependencies` L38. | Manifest wins → **Django ≥ 6.0.7 required**. README badge + classifiers are stale/incorrect. Owner should update them. Already flagged in `ARCHITECTURE.md` Note 1. |
| C-2 | Language on disk: chrysa standard is English-on-disk, but `ARCHITECTURE.md`, `legal/cgu.md`, `legal/mentions-legales.md` are in French. | Those files; STANDARDS (English-on-disk). | Legal docs in French may be intentional (French jurisdiction, LCEN). `ARCHITECTURE.md` in French is a likely standards drift. Owner decision. |
| C-3 | CLAUDE.md says `tests/integration/` is "Phase 4+ (empty)", but it contains `test_packaging.py` (+`__init__.py`). | `tests/integration/`. | CLAUDE.md is stale; integration tests now exist. |
| C-4 | CLAUDE.md `install()` docstring/description says "middleware and signal handlers", while ADR-0001 chose `execute_wrapper` explicitly over signals. | `__init__.py` install() docstring; ADR-0001. | Wording drift — "signal handlers" likely inaccurate; verify what `bootstrap()` actually registers. |

## Stale / drift

- README roadmap, CLAUDE.md project-state table, and new ROADMAP.md agree on phases — keep them in lockstep on the next change (three copies of the same table is duplication debt).
- `legal/*` and `docs/reference/github-inspiration.md` were not fully audited.

## Gaps / documentation debt

- **DECISIONS**: only ADR-0001 exists as a file; DEC-002…DEC-008 live only in CLAUDE.md prose. PROPOSAL: promote to numbered ADRs.
- **Benchmark**: `.benchmarks/` dir exists at root but the ADR-0001 kill-test benchmark is declared unimplemented — reconcile (is the gate closed or not?).
- **OBSERVABILITY doc skipped**: this is a dev-time library with no runtime service, metrics, or logging pipeline of its own; an OBSERVABILITY.md would be empty. Recorded as intentionally skipped.
- **PRD doc skipped**: README already serves as product/overview; a separate PRD would duplicate it. Recorded as intentionally skipped.
- **`fastapi-query-optimizer` port relationship** (task brief) is not evidenced anywhere in this repo — cannot verify from here.

## Docs generated this pass (root only)

REQUIREMENTS.md, CONSTRAINTS.md, DECISIONS.md, TESTING.md, SECURITY.md, GLOSSARY.md, ROADMAP.md, REVIEW.md.

## Docs preserved (not modified)

README.md, ARCHITECTURE.md, CHANGELOG.md, CONTRIBUTING.md, AGENTS.md, CLAUDE.md, ai-instructions.md, handover.md, primer.md, docs/adr/*, legal/*.
