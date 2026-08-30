# CLAUDE.md — django-query-optimizer

> Read `.github/copilot-instructions.md` and `AGENTS.md` before starting any task.
> Updated: 2026-05-16

## Purpose

Python library that detects N+1 queries, duplicate queries, slow queries, and missing indexes
in Django applications — at development time, in the test suite, and in VS Code (Phase 4 in progress).

---

## Project State

| Phase | Status |
|---|---|
| 1a — Core (collector, analyzer, slow/duplicate detectors) | ✅ Done |
| 1b — HTTP Middleware (`QueryOptimizerMiddleware`) | ✅ Done |
| 1c — Admin dashboard | ✅ Done |
| 2a — N+1 detector (`NplusOneDetector`) | ✅ Done |
| 2b — DRF serializer N+1 detector (`DRFSerializerDetector`) | ✅ Done |
| 2c — FK detector (`SelectRelatedDetector`) | ✅ Done |
| 2d — Query scoring (`QueryScorer`) | ✅ Done |
| 3 — pytest SARIF report + `RegressionDetector` | ✅ Done |
| 4 — VS Code extension (reads SARIF) | 🚧 In Progress |
| 5 — Multi-framework | Planned |

Current version: **0.1.0** (pre-alpha, unreleased on PyPI).

**Phase 4 repos:**
- Pytest plugin `--sarif-output`: PR [#22](https://github.com/chrysa/django-query-optimizer/pull/22) ✅ merged — SARIF prerequisite shipped in this repo.
- VS Code extension (active dev): [`chrysa/django-query-optimizer-vscode`](https://github.com/chrysa/django-query-optimizer-vscode)

---

## Architecture (quick map)

```
src/django_query_optimizer/
├── __init__.py                 → public API: QueryCollector, QueryAnalyzer,
│                                             ORMRecommendation, QueryOptimizerMiddleware,
│                                             NplusOneDetector, SelectRelatedDetector,
│                                             DRFSerializerDetector, QueryScorer,
│                                             QueryStore, RequestRecord,
│                                             RegressionDetector, SARIFReporter, install()
├── _internal/bootstrap.py      → idempotent Django hook registration
├── collectors/query_collector.py → CapturedQuery + QueryCollector (execute_wrapper)
├── middleware/query_collector_middleware.py → per-request collector, sets endpoint
├── analyzers/query_analyzer.py   → slow_query + duplicate_query detectors
├── detectors/
│   ├── base.py                   → BaseDetector protocol
│   ├── n_plus_one.py             → NplusOneDetector
│   ├── select_related.py         → SelectRelatedDetector
│   └── drf_serializer.py         → DRFSerializerDetector (Phase 2b)
├── recommendations/base.py       → ORMRecommendation frozen dataclass + Severity enum
├── scoring/query_scorer.py       → QueryScorer — 0-100 health score + letter grade
├── regression/detector.py        → RegressionDetector — baseline compare + JSON persist
├── reporting/sarif.py            → SARIFReporter — SARIF 2.1 output for VS Code / CI
├── store.py                      → QueryStore + RequestRecord — in-memory request history
├── admin/                        → Django Admin dashboard
└── testing/pytest_plugin.py      → pytest entry-point + query_collector fixture
```

---

## Key Design Decisions

- **`execute_wrapper`** (not signals or middleware) — lower overhead, works in tests without HTTP.
- **Frozen dataclass** for `ORMRecommendation` — hashable, sortable, immutable.
- **`StrEnum` Severity** — allows `rec.severity == "high"` comparisons without importing the enum.
- **Threshold constants at module level** (`SLOW_QUERY_THRESHOLD_MS`, `DUPLICATE_MIN_COUNT`) — easy to override in tests.
- **pytest plugin registered via `entry-points`** — zero-config activation after `pip install`.

---

## Commands

```bash
make docker-test    # full test suite + coverage (CI target)
make lint-all       # ruff check + mypy (lint + typecheck)
make pre-commit     # run all pre-commit hooks on every file
make install-dev    # local dev install (not for test execution)
```

> **Never run pytest / ruff / mypy directly on the host.** Always use `make` targets.

---

## Test Layout

```
tests/
├── conftest.py          # shared fixtures (Django settings module)
├── settings.py          # minimal Django settings for tests
├── unit/
│   ├── test_admin.py
│   ├── test_init.py                    # public API surface smoke test
│   ├── test_middleware.py
│   ├── test_n_plus_one_detector.py
│   ├── test_drf_serializer_detector.py # DRFSerializerDetector unit tests
│   ├── test_pytest_plugin.py
│   ├── test_query_analyzer.py          # QueryAnalyzer detector unit tests
│   ├── test_query_collector.py         # QueryCollector unit tests
│   ├── test_query_scorer.py
│   ├── test_recommendations.py         # ORMRecommendation + Severity unit tests
│   ├── test_regression_detector.py
│   ├── test_sarif_reporter.py
│   ├── test_select_related_detector.py
│   └── test_store.py
└── integration/                        # Phase 4+ (empty)
```

Coverage threshold: **85%** (enforced by `pytest-cov` with `fail_under = 85`).

---

## Adding a New Detector

1. Create `src/django_query_optimizer/detectors/<name>.py` implementing `detect(queries) -> list[ORMRecommendation]`.
2. Export the class from `__init__.py` and add it to `__all__`.
3. Write a matching test class in `tests/unit/test_<name>_detector.py`.
4. Update the detector table in `README.md` and this file.
5. Use an existing `Severity` level or add to the enum if justified.

---

## Conventions

- Public API exports live in `__init__.py.__all__` — nothing else is considered stable.
- No breaking changes without a major version bump.
- All type annotations must pass `mypy --strict`.
- Commit identity: `user.name=chrysa`, `user.email=greau.anthony+chrysa@gmail.com`.


- `testing-pytest/SKILL.md` — pytest DDD + pytest-mock + constants (load when writing tests)

- `dockerfile-multistage/SKILL.md` — 4-stage Python 3.14 containers (load when editing Dockerfile)

Shared skills from `shared-standards/.claude/skills/`:

- `ui-ux/SKILL.md` — UX/UI/ergonomics across ALL surfaces (web, CLI, VS Code, Discord, desktop, game, agent) + WCAG 2.1 AA + dark mode + i18n FR+EN (load when building any human-facing surface)


<!-- chrysa:standards:start · managed by distribute-standards.sh · DO NOT EDIT -->
# chrysa — Transverse Standards (core)

> The **slim always-on core**. The canonical, tool-agnostic source of truth is `standards/STANDARDS.chrysa.md`; the normative annexes live under `standards/annexes/`. Each rule below is a one-line pointer — its full text lives in the per-domain file named beside the heading (`standards/rules/<domain>.md`), read on demand.

**Where an annexe and the canon disagree, the canon wins.**

### Governance, language & compliance · `standards/rules/governance.md`
- Normative annexes
- Language
- Compliance targets
- Governance — strategic pillars & ADR format

### Cross-cutting stack · `standards/rules/stack.md`
- Cross-cutting stack (settled ADRs — do not relitigate)

### SCM — branches, commits & pull requests · `standards/rules/scm.md`
- Commits
- Branches
- Branch model — `main` is production, `develop` is the workspace
- Merge
- One PR per issue
- Issues and PRs are type-driven

### Architecture, decoupling & portability · `standards/rules/architecture.md`
- Repo provenance — every code repo depends on `project-init`
- Every repo declares its profile and DDD level
- Projects talk through versioned contracts only
- Everything is machine-agnostic and portable — no rule, repo, or script is bound to one machine
- Every external server the service talks to is addressed through the environment — never hardcoded
- Every tracked file and folder must earn its place — a repo holds only what is useful to it now
- The repository architecture is legible to an agent — optimised for Claude, not only for humans
- Deferred work is a governed job, not a fire-and-forget

### Testing · `standards/rules/testing.md`
- Tests: pytest only
- Frontend tests: Vitest + Testing Library + MSW — from the scaffold, not later

### Frontend & web semantics · `standards/rules/frontend.md`
- TypeScript is strict by contract
- The JS/TS package manager is `pnpm` — `npm` and `yarn` are forbidden
- React is a presentation layer, not the domain
- The frontend says when the backend is unreachable or unstable
- The frontend is reactive and real-time by default
- UI state survives reload & focus
- Everything is semantic — the markup, the data, and the URLs
- URL-addressable frontend navigation — mandatory

### APIs, contracts & real-time · `standards/rules/api.md`
- A real-time backend has channel contracts and never blocks
- APIs, SDKs & public contracts follow the `STD-API-001` contract

### Accessibility · `standards/rules/accessibility.md`
- Dark mode
- Every site is usable by the majority of disabilities — not only the screen-reader case

### Documentation & session state · `standards/rules/docs.md`
- Notion logging
- Documentation and Notion are maintained in lockstep with the code — a change that leaves them stale is unfinished
- Session lifecycle (primer + memory + hindsight)

### AI agents & features · `standards/rules/agents.md`
- Agent actions are governed
- An AI feature is evaluated, not just shipped
- An agent writes only where the owner owns

### Security, identity & sessions · `standards/rules/security.md`
- Per-person data implies a user account — no exceptions dressed up as simplicity
- Identity goes through the cluster SSO first
- A session is secured and it expires
- Every form is a hostile input surface — validate on the server, always

### Code quality & anti-patterns · `standards/rules/code-quality.md`
- No hardcoded constants
- No literal HTTP status codes — use the constants the framework already ships
- No code duplication — the second occurrence is an extraction order
- Raised errors are typed
- Failures are contained, and observable
- Prefer a lookup table to a state machine
- Decompose into small, independently unit-testable methods
- Code is read far more often than it is written — optimise for the reader, and standardise the form
- Avoid lambdas and anonymous constructs — a named function is the default
- Basic optimisations and known anti-patterns are caught in review and in CI
- A cache is a correctness contract, not a sprinkle of speed
- Quality gates
- Error handling pattern (all automations)

### Backend Python · `standards/rules/backend-python.md`
- Python packaging — `pyproject.toml` is the single source of truth
- Python is written object-oriented, one class per file
- Import the item, not the module — `from x import y; y()`
- Functions and methods are called with named arguments — positional call sites are the exception, not the rule

### Data, persistence & migrations · `standards/rules/data.md`
- Data, persistence & migrations follow the `STD-DATA-001` contract

### Observability & operations · `standards/rules/observability.md`
- Observability & production readiness follow the `STD-OPS-001` contract
- The container is versioned separately from the application it hosts, and an admin can see what is actually deployed
- Observability — Sentry → GitHub issues (norm)

### Containers & compose · `standards/rules/containers.md`
- External dependencies are installed in containers, never on the host
- No virtualenv in a repo — ever
- Tool caches & deps never touch the project tree
- Dockerfiles are multi-stage, with a `production` and a `dev` stage — mandatory
- App containers ship the app only — the platform layer is the owner's responsibility
- Only a publicly useful port is published — everything else stays on the container network
- A compose file is minimal — declare only what the stack needs, default the rest
- Dev stage must hot-reload
- Local dev runs the code in-container, live, in debug mode — never the production server
- `.dockerignore` mandatory & exhaustive
- Container-runtime policy

### Product surfaces · `standards/rules/product.md`
- Setup wizard & config panel
- A game is DRM-free and fully playable solo offline
- Every product that is operated ships a management backoffice
- If a user can supply a file, the product accepts an upload
- A floating assistant where it earns its place — never as decoration

### Design system · `standards/rules/design.md`
- Design system

### Developer loop & tooling · `standards/rules/dev-loop.md`
- Makefile targets
- Shared skills (load on demand from shared-standards/.claude/skills/)

### CI/CD, pre-commit & release · `standards/rules/ci-cd.md`
- Release & changelog config (canonical)
- GitHub Actions (reuse first · custom actions centralised · thin workflows)
- Pre-commit & git hooks (native, via pre-commit.com — never wrapped in make)
<!-- chrysa:standards:end -->
