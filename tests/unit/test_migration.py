"""Unit tests for the initial migration module."""

from __future__ import annotations

import importlib


class TestInitialMigration:
    def test_declares_unmanaged_querylog_model(self) -> None:
        module = importlib.import_module("django_query_optimizer.migrations.0001_initial")

        migration = module.Migration
        assert migration.initial is True
        assert migration.dependencies == []
        assert [op.name for op in migration.operations] == ["QueryLog"]
        assert migration.operations[0].options["managed"] is False
