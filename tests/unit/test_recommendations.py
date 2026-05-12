"""Unit tests for ORMRecommendation."""

from __future__ import annotations

from django_query_optimizer.recommendations.base import ORMRecommendation, Severity


class TestORMRecommendation:
    def test_frozen(self) -> None:
        rec = ORMRecommendation(
            issue_type="test",
            severity=Severity.LOW,
            message="msg",
            suggestion="fix",
        )
        import dataclasses

        try:
            dataclasses.fields(rec)  # sanity check it is a dataclass
            rec.issue_type = "other"  # type: ignore[misc]
        except (AttributeError, TypeError, dataclasses.FrozenInstanceError):
            pass  # expected: frozen dataclass raises on assignment
        else:
            raise AssertionError("Expected FrozenInstanceError was not raised")

    def test_default_fields(self) -> None:
        rec = ORMRecommendation(
            issue_type="n_plus_1",
            severity=Severity.HIGH,
            message="N+1 detected",
            suggestion="Use select_related()",
        )
        assert rec.python_file == ""
        assert rec.python_line == 0

    def test_ordering_critical_before_low(self) -> None:
        critical = ORMRecommendation(issue_type="a", severity=Severity.CRITICAL, message="", suggestion="")
        low = ORMRecommendation(issue_type="b", severity=Severity.LOW, message="", suggestion="")
        assert critical < low

    def test_severity_enum_values(self) -> None:
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"
