#!make
ifneq (,)
	$(error This Makefile requires GNU Make)
endif

# ─── Variables ────────────────────────────────────────────────────────────────
PROJECT_NAME ?= django-query-optimizer
PYTHON       ?= python3
PIP          ?= pip
PACKAGE_DIR   = django_query_optimizer
SRC_DIR       = src/$(PACKAGE_DIR)

.DEFAULT_GOAL := help

.PHONY: $(shell grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | cut -d":" -f1 | tr "\n" " ")

help: ## Display this help message
	@echo "==================================================================="
	@echo "  $(PROJECT_NAME)"
	@echo "==================================================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "==================================================================="

# ─── Installation ─────────────────────────────────────────────────────────────

install: ## Install package dependencies
	$(PIP) install -e "."

install-dev: ## Install package + dev dependencies
	$(PIP) install -e ".[dev,postgres,drf]"

install-pre-commit: ## Install and configure git pre-commit hooks
	$(PIP) install --quiet pre-commit
	pre-commit install
	pre-commit autoupdate --bleeding-edge

# ─── Quality ──────────────────────────────────────────────────────────────────

lint: ## Run ruff linting (via Docker)
	docker compose run --rm lint

format: ## Run ruff formatter
	docker compose run --rm lint sh -c "ruff format $(SRC_DIR)"

format-check: ## Check ruff formatting (no changes)
	docker compose run --rm lint sh -c "ruff format --check $(SRC_DIR)"

typecheck: ## Run mypy type checking (via Docker)
	docker compose run --rm lint sh -c "mypy $(SRC_DIR)"

pre-commit: ## Run pre-commit on all files
	pre-commit run --all-files

# ─── Tests ────────────────────────────────────────────────────────────────────

test: ## Run tests (via Docker)
	$(MAKE) docker-test

test-cov: ## Run tests with coverage report (via Docker)
	$(MAKE) docker-test

# ─── Docker ───────────────────────────────────────────────────────────────────

docker-build: ## Build all Docker stages
	docker compose build

docker-up: ## Start services with Docker Compose
	docker compose up -d

docker-down: ## Stop services
	docker compose down

docker-test: ## Run tests inside Docker container
	docker compose run --rm test

docker-lint: ## Run lint + type-check inside Docker container
	docker compose run --rm lint

docker-clean: ## Remove Docker images and containers for this project
	docker compose down --rmi local --volumes --remove-orphans

# ─── Build & Release ──────────────────────────────────────────────────────────

build: ## Build Python package
	$(MAKE) docker-build

changelog: ## Generate CHANGELOG.md via git-cliff
	git-cliff -o CHANGELOG.md

# ─── Cleanup ──────────────────────────────────────────────────────────────────

clean: ## Clean build artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info src/*.egg-info

# ─── Compat aliases ───────────────────────────────────────────────────────────

dev: install-dev ## Setup development environment
type-check: typecheck ## Legacy alias
