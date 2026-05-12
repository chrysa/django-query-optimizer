# ── Stage 1: deps — install production dependencies ───────────────────────────
FROM python:3.14-slim AS deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip setuptools>=70 wheel

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

# ── Stage 2: test — run the full test suite ───────────────────────────────────
FROM deps AS test

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir ".[dev,postgres,drf]"

COPY tests/ ./tests/

CMD ["pytest", "tests", "-v", \
    "--cov=django_query_optimizer", \
    "--cov-report=xml:/app/coverage.xml", \
    "--cov-report=term-missing", \
    "--cov-fail-under=85"]

# ── Stage 3: lint — ruff + mypy quality checks ────────────────────────────────
FROM test AS lint

CMD ["sh", "-c", "ruff check src/django_query_optimizer && mypy src/django_query_optimizer"]

# ── Stage 4: production — minimal library image ───────────────────────────────
FROM python:3.14-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser appuser

RUN pip install --no-cache-dir --upgrade pip setuptools>=70 wheel

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

USER appuser

HEALTHCHECK CMD python -c "import django_query_optimizer; print('ok')" || exit 1

CMD ["python", "-c", "import django_query_optimizer; print(django_query_optimizer.__version__)"]
