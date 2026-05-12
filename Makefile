#!make
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

.DEFAULT_GOAL := help

.PHONY: help install install-dev pre-commit pre-commit-update \
        lint format format-check typecheck lint-all \
        test test-fast \
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

docker-test: ## Build and run tests via Docker (CI target)
	$(DC) build test
	$(DC_RUN) test

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
