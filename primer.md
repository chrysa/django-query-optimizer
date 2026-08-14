# primer — django-query-optimizer

> Read this before `CLAUDE.md`. Current state + what to do now.

## State (2026-08-14)

- Core lib phases **1a–3 complete**: collector, analyzer (slow + duplicate),
  detectors (N+1, select_related, DRF), scoring, regression, SARIF, pytest plugin.
- Version **0.1.0**, pre-alpha, unreleased on PyPI.
- Phase 4 (VS Code extension) lives in `chrysa/django-query-optimizer-vscode`;
  the SARIF prerequisite (PR #22) is merged here.

## Do now / open threads

- Open PR for branch `chore/fix-claude-settings-hooks` (hook-schema fix) — pushed,
  PR blocked by `gh` collaborator rights.
- Dependabot #174/175/176 awaiting merge.
- ADR benchmark gate (ADR-0001) open: no `execute_stack` overhead benchmark yet.
- Known functional gaps: N+1/duplicate double-flagging, score not normalised to
  query count (see `.claude/memory/known-issues.md`).

## Commands

`make docker-test` (gate), `make lint-all`, `make ci`. Never run pytest on host.
