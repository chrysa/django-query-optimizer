"""Unit tests for public __init__ API."""

from __future__ import annotations


class TestPublicAPI:
    def test_version_is_string(self) -> None:
        import django_query_optimizer

        assert isinstance(django_query_optimizer.__version__, str)
        parts = django_query_optimizer.__version__.split(".")
        assert len(parts) == 3

    def test_all_exports_importable(self) -> None:
        import django_query_optimizer

        for name in django_query_optimizer.__all__:
            assert hasattr(django_query_optimizer, name), f"Missing export: {name}"

    def test_install_is_idempotent(self) -> None:
        import django_query_optimizer

        django_query_optimizer.install()
        django_query_optimizer.install()  # second call — must not raise
