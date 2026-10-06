#!make
# makefile-tier: python-app
ifneq (,)
	$(error This Makefile requires GNU Make)
endif

# ─── Variables ────────────────────────────────────────────────────────────────
PROJECT_NAME ?= django-query-optimizer
PACKAGE_DIR   = django_query_optimizer
SRC_DIR       = src/$(PACKAGE_DIR)
TESTS_DIR     = tests

DC      := docker compose
DC_RUN  := $(DC) run --rm

# Compatibility matrix for `make docker-test-matrix`
MATRIX_PYTHON ?= 3.13 3.14
MATRIX_DJANGO ?= 5.2 6.0

.DEFAULT_GOAL := help

.PHONY: help install install-dev pre-commit pre-commit-update \
        lint format format-check typecheck lint-all \
        test test-cov test-fast docker-test docker-test-matrix \
        dev \
        build build-cache \
        docker-up docker-down docker-clean \
        changelog clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?##"}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ─── Installation ─────────────────────────────────────────────────────────────

install: ## Install package dependencies (local)
	pip install -e "."

install-dev: ## Install package + dev dependencies (local)
	pip install -e ".[dev,postgres,drf]"

# ─── Quality ──────────────────────────────────────────────────────────────────

lint: ## Run ruff check (via Docker)
	$(DC_RUN) lint

format: ## Run ruff format (via Docker)
	$(DC_RUN) lint sh -c "ruff format $(SRC_DIR)"

format-check: ## Check ruff formatting without changes (via Docker)
	$(DC_RUN) lint sh -c "ruff format --check $(SRC_DIR)"

typecheck: ## Run mypy type checking (via Docker)
	$(DC_RUN) lint sh -c "mypy $(SRC_DIR)"

lint-all: lint typecheck ## Run lint + typecheck

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks to latest versions
	pre-commit autoupdate --bleeding-edge

# ─── Tests ────────────────────────────────────────────────────────────────────

test: ## Run tests with coverage (via Docker)
	$(DC_RUN) test

test-cov: ## Run tests with coverage report (alias → test)
	$(MAKE) test

dev: ## Start development environment (alias → docker-up)
	$(MAKE) docker-up

docker-test: ## Build and run tests via Docker (CI target)
	@# Pre-create coverage.xml as a file so the bind-mount maps file->file
	@# (Docker auto-creates a *directory* for a missing bind source, which
	@# then makes coverage's open(path,"w") fail). -T disables the pseudo-TTY
	@# so this also runs in CI / non-interactive contexts.
	@rm -rf coverage.xml
	@touch coverage.xml
	$(DC) build test
	$(DC_RUN) -T test

docker-test-matrix: ## Run tests in Docker across Python x Django (override MATRIX_PYTHON / MATRIX_DJANGO)
	@fail=0; for py in $(MATRIX_PYTHON); do for dj in $(MATRIX_DJANGO); do \
		echo "=== Python $$py / Django $$dj ==="; \
		rm -rf coverage.xml; touch coverage.xml; \
		PYTHON_VERSION=$$py DJANGO_VERSION=$$dj $(DC) build test >/dev/null \
		&& PYTHON_VERSION=$$py DJANGO_VERSION=$$dj $(DC_RUN) -T test || fail=1; \
	done; done; exit $$fail

test-fast: ## Run tests without coverage (fast, via Docker)
	$(DC_RUN) test sh -c "pytest $(TESTS_DIR) -v"

# ─── Build ────────────────────────────────────────────────────────────────────

build: ## Build Docker images (no cache)
	$(DC) build --no-cache

build-cache: ## Build Docker images (with cache)
	$(DC) build

# ─── Docker helpers ───────────────────────────────────────────────────────────

docker-up: ## Start services (detached)
	$(DC) up -d

docker-down: ## Stop services
	$(DC) down

docker-clean: ## Remove images, volumes, orphan containers
	$(DC) down --rmi local --volumes --remove-orphans

# ─── Release ──────────────────────────────────────────────────────────────────

changelog: ## Generate CHANGELOG.md via git-cliff
	git-cliff -o CHANGELOG.md

# ─── Cleanup ──────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build $(REPORTS_DIR)

# ─── CI gate ────────────────────────────────────
ci: lint typecheck test ## Run the full local gate (lint + typecheck + test)
