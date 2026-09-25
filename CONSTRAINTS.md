# Constraints — django-query-optimizer

> Tagged FACT (verifiable), INFERENCE (deduced), UNKNOWN. Where README and `pyproject.toml`
> disagree, the manifest is authoritative (see CONTRADICTIONS).

## Runtime / platform

- **Python 3.14** — sole classifier `Programming Language :: Python :: 3.14`; bytecode compiled as `cpython-314`. FACT
- **Django runtime dependency `django>=6.0.7`** — `pyproject.toml [project].dependencies`. FACT. This **contradicts** the README badge "django 4.2+" and the `Framework :: Django :: 4.2/5.0/5.1` classifiers (see CONTRADICTIONS). Manifest wins.
- **Capture mechanism**: Django `connection.execute_wrappers` (not signals, not `connection.queries`). ADR-0001. FACT
- **Development-only**: `install()` and `QueryOptimizerMiddleware` must never be added to production settings (added query/wrapper overhead). FACT (README Warning)

## Optional dependencies (extras)

- `postgres` → `psycopg2-binary>=2.9`; `drf` → `djangorestframework>=3.14`; `realtime` → `channels>=4.0`, `daphne>=4.2.2`. FACT (`pyproject.toml`)

## Build & packaging

- Build backend: `setuptools>=70` + `wheel` (`setuptools.build_meta`). FACT
- Wheel must include non-Python data (admin `change_list.html`, `py.typed`) via `**` globs; setuptools default would silently drop them (documented in `pyproject.toml`). FACT
- Version single source of truth: `pyproject.toml [project].version` = **0.1.0**; re-exported via `_internal/version.py` using `importlib.metadata`. FACT
- Distribution status: pre-alpha, **not released on PyPI**. FACT (CLAUDE.md)

## Development loop (chrysa standards)

- **Containers-only**: pytest / ruff / mypy must run via `make` targets in Docker, never on the host. FACT (CLAUDE.md, Makefile, docker-compose services `lint`/`test`). A `.claude/hookify.warn-host-test-lint.local.md` hook warns on host runs.
- **English-on-disk** is the chrysa standard — but `ARCHITECTURE.md` and `legal/*` are in French (see CONTRADICTIONS). FACT
- Commit identity: `user.name=chrysa`, `user.email=greau.anthony+chrysa@gmail.com`. FACT (CLAUDE.md)
- Coverage gate 85% and mypy-strict are CI-enforced. FACT

## Testing constraint (relevant to this doc task)

- The package **is** a pytest plugin (`pytest11` entry-point registering `--query-analysis`). Running this repo's own tests from another context may require `-p no:query_optimizer` to avoid the plugin self-loading. INFERENCE (matches sibling repos' memory notes; not verified here).

## Quality tooling

- ruff pinned to Python 3.13 target in one place because `ruff format <=0.15.15` strips multi-except parens under py314 — to be restored upstream. FACT (`pyproject.toml` comment)
- `examples/`, `.claude/`, `scripts/quality_gate.py` excluded from ruff. FACT
