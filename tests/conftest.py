"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_query_store() -> None:
    """Reset the QueryStore singleton between tests to prevent state leakage."""
    from django_query_optimizer.store import QueryStore

    QueryStore.reset()
    yield  # type: ignore[misc]
    QueryStore.reset()
