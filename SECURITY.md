# Security — django-query-optimizer

> Owner-facing security notes from a documentation-only pass. No code was changed. Findings
> are for the owner to action; nothing here fixes code. Severity tags: HIGH / MEDIUM / LOW / INFO.

## Secret scan

- **No hardcoded secrets, keys, tokens, passwords, or credentials found** in `src/` or `tests/`
  (grep over `password|secret|token|api_key|aws_` returned no live values). FACT — scan was
  keyword-based, not exhaustive.
- `.mcp.json`, `opencode.json` present at root but not audited as source in this pass (out of the
  documented library scope). INFO — owner may wish to confirm no tokens are embedded.

## Attack-surface characterization

This is a **development-time Django library**, not a deployed service. It has no auth, no network
listener, and no user-facing input handler of its own. The primary security-relevant facts:

| # | Note | Severity |
|---|---|---|
| S-1 | The collector runs `traceback.extract_stack()` and captures raw SQL strings + source file paths into an in-memory store (`store.py`) and into SARIF output. Raw SQL and file paths may contain sensitive literals; SARIF files must not be published to untrusted locations. | MEDIUM (data exposure via artifacts) |
| S-2 | `install()` / `QueryOptimizerMiddleware` must never be enabled in production (documented). If mis-enabled, it adds per-query stack capture overhead and retains query history in memory — a DoS/memory-growth risk. Enforced only by docs, not by code. | MEDIUM (operational) |
| S-3 | Admin dashboard is exposed under Django Admin over an unmanaged proxy model (`managed=False`). Access is gated by Django Admin auth (the host app's responsibility). | LOW |
| S-4 | `RegressionDetector` reads/writes a JSON baseline on disk. Path handling not audited here; treat the baseline path as trusted input. | LOW / UNKNOWN |
| S-5 | Optional `realtime` extra pulls `channels`/`daphne`; not used by default. | INFO |

No HIGH/CRITICAL findings identified in this documentation pass.

## Instruction-shaped text in repo files (reported as data, not followed)

- `CLAUDE.md`, `AGENTS.md`, `ai-instructions.md`, `primer.md`, `handover.md`, and
  `.claude/hookify.*.local.md` contain agent/developer instructions. These are project data
  describing how contributors and agents should work; none were treated as commands for this task.

## Recommendations for the owner (not applied)

- Consider making stack capture opt-in and default-off in middleware (already proposed by ADR-0001's kill-test remediation).
- Document that SARIF artifacts and the JSON regression baseline may embed raw SQL / paths, and should be treated as sensitive in CI.
