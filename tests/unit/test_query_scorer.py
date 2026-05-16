"""Unit tests for QueryScorer and QueryScore."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from django_query_optimizer.recommendations.base import ORMRecommendation, Severity
from django_query_optimizer.scoring.query_scorer import (
    MAX_SCORE,
    MIN_SCORE,
    PENALTY_CRITICAL,
    PENALTY_HIGH,
    PENALTY_INFO,
    PENALTY_LOW,
    PENALTY_MEDIUM,
    QueryScore,
    QueryScorer,
)


def _rec(severity: Severity) -> ORMRecommendation:
    return ORMRecommendation(
        issue_type="test",
        severity=severity,
        message="test message",
        suggestion="test suggestion",
    )


class TestQueryScoreDataclass:
    """QueryScore is a frozen dataclass with correct fields."""

    def test_fields_accessible(self) -> None:
        score = QueryScore(value=80, grade="B", summary="ok", counts={"critical": 0})
        assert score.value == 80
        assert score.grade == "B"
        assert score.summary == "ok"
        assert score.counts == {"critical": 0}

    def test_frozen(self) -> None:
        score = QueryScore(value=80, grade="B", summary="ok", counts={})
        with pytest.raises(FrozenInstanceError):
            score.value = 50  # type: ignore[misc]


class TestQueryScorerNoIssues:
    """Score with an empty recommendation list."""

    def test_perfect_score(self) -> None:
        scorer = QueryScorer([])
        result = scorer.compute()
        assert result.value == MAX_SCORE

    def test_grade_a(self) -> None:
        result = QueryScorer([]).compute()
        assert result.grade == "A"

    def test_summary_no_issues(self) -> None:
        result = QueryScorer([]).compute()
        assert "no issues" in result.summary
        assert "100/100" in result.summary

    def test_all_counts_zero(self) -> None:
        result = QueryScorer([]).compute()
        for sev in ("critical", "high", "medium", "low", "info"):
            assert result.counts[sev] == 0


class TestQueryScorerPenalties:
    """Each severity subtracts the correct number of points."""

    def test_single_critical(self) -> None:
        result = QueryScorer([_rec(Severity.CRITICAL)]).compute()
        assert result.value == MAX_SCORE - PENALTY_CRITICAL

    def test_single_high(self) -> None:
        result = QueryScorer([_rec(Severity.HIGH)]).compute()
        assert result.value == MAX_SCORE - PENALTY_HIGH

    def test_single_medium(self) -> None:
        result = QueryScorer([_rec(Severity.MEDIUM)]).compute()
        assert result.value == MAX_SCORE - PENALTY_MEDIUM

    def test_single_low(self) -> None:
        result = QueryScorer([_rec(Severity.LOW)]).compute()
        assert result.value == MAX_SCORE - PENALTY_LOW

    def test_single_info(self) -> None:
        result = QueryScorer([_rec(Severity.INFO)]).compute()
        assert result.value == MAX_SCORE - PENALTY_INFO

    def test_combined_penalties(self) -> None:
        recs = [_rec(Severity.HIGH), _rec(Severity.MEDIUM), _rec(Severity.LOW)]
        result = QueryScorer(recs).compute()
        expected = MAX_SCORE - PENALTY_HIGH - PENALTY_MEDIUM - PENALTY_LOW
        assert result.value == expected

    def test_clamped_to_zero(self) -> None:
        recs = [_rec(Severity.CRITICAL)] * 10
        result = QueryScorer(recs).compute()
        assert result.value == MIN_SCORE

    def test_never_negative(self) -> None:
        recs = [_rec(Severity.CRITICAL)] * 100
        result = QueryScorer(recs).compute()
        assert result.value >= MIN_SCORE


class TestQueryScorerGrades:
    """Grade thresholds map correctly to letters."""

    @pytest.mark.parametrize(
        ("recs", "expected_grade"),
        [
            ([], "A"),  # 100 → A
            ([_rec(Severity.INFO)] * 10, "A"),  # 90 → A
            ([_rec(Severity.INFO)] * 11, "B"),  # 89 → B
            ([_rec(Severity.MEDIUM)] * 3, "B"),  # 76 → B
            ([_rec(Severity.MEDIUM)] * 4, "C"),  # 68 → C  (100 - 32 = 68)
            ([_rec(Severity.HIGH)] * 4, "D"),  # 40 → D   (100 - 60 = 40)
        ],
    )
    def test_grade_parametrized(self, recs: list[ORMRecommendation], expected_grade: str) -> None:
        result = QueryScorer(recs).compute()
        assert result.grade == expected_grade

    def test_grade_f_at_zero(self) -> None:
        recs = [_rec(Severity.CRITICAL)] * 10
        result = QueryScorer(recs).compute()
        assert result.grade == "F"

    def test_grade_d_range(self) -> None:
        # 100 - 3*25 = 25 → D (threshold 25 = D)
        recs = [_rec(Severity.CRITICAL)] * 3
        result = QueryScorer(recs).compute()
        assert result.grade == "D"

    def test_grade_b_boundary(self) -> None:
        # 100 - INFO*10 = 90 → A, 11 = 89 → B
        assert QueryScorer([_rec(Severity.INFO)] * 10).compute().grade == "A"
        assert QueryScorer([_rec(Severity.INFO)] * 11).compute().grade == "B"

    def test_grade_a_boundary(self) -> None:
        # Exactly 90 → A
        recs = [_rec(Severity.INFO)] * 10  # 100 - 10 = 90
        assert QueryScorer(recs).compute().grade == "A"


class TestQueryScorerCounts:
    """Per-severity counts are accurate."""

    def test_counts_single_critical(self) -> None:
        result = QueryScorer([_rec(Severity.CRITICAL)]).compute()
        assert result.counts["critical"] == 1

    def test_counts_mixed(self) -> None:
        recs = [
            _rec(Severity.CRITICAL),
            _rec(Severity.CRITICAL),
            _rec(Severity.HIGH),
            _rec(Severity.INFO),
        ]
        result = QueryScorer(recs).compute()
        assert result.counts["critical"] == 2
        assert result.counts["high"] == 1
        assert result.counts["medium"] == 0
        assert result.counts["low"] == 0
        assert result.counts["info"] == 1

    def test_counts_all_severities(self) -> None:
        recs = [_rec(s) for s in Severity]
        result = QueryScorer(recs).compute()
        for sev in ("critical", "high", "medium", "low", "info"):
            assert result.counts[sev] == 1


class TestQueryScorerSummary:
    """Summary string contains expected content."""

    def test_summary_contains_score(self) -> None:
        result = QueryScorer([_rec(Severity.HIGH)]).compute()
        expected_value = MAX_SCORE - PENALTY_HIGH
        assert f"{expected_value}/{MAX_SCORE}" in result.summary

    def test_summary_contains_grade(self) -> None:
        result = QueryScorer([]).compute()
        assert "(A)" in result.summary

    def test_summary_contains_count(self) -> None:
        recs = [_rec(Severity.HIGH), _rec(Severity.MEDIUM)]
        result = QueryScorer(recs).compute()
        assert "2 issue(s)" in result.summary

    def test_summary_lists_active_severities_only(self) -> None:
        result = QueryScorer([_rec(Severity.HIGH)]).compute()
        assert "high" in result.summary
        assert "critical" not in result.summary
        assert "medium" not in result.summary

    def test_summary_zero_issues(self) -> None:
        result = QueryScorer([]).compute()
        assert "0 issue(s)" in result.summary
        assert "no issues" in result.summary


class TestQueryScorerIntegration:
    """Integration: QueryScorer works on real ORMRecommendation objects."""

    def test_real_recommendation_objects(self) -> None:
        recs = [
            ORMRecommendation(
                issue_type="slow_query",
                severity=Severity.HIGH,
                message="Query took 200ms",
                suggestion="Add index",
                python_file="views.py",
                python_line=12,
            ),
            ORMRecommendation(
                issue_type="n_plus_one",
                severity=Severity.CRITICAL,
                message="N+1 detected",
                suggestion="Use select_related()",
            ),
        ]
        result = QueryScorer(recs).compute()
        assert result.value == MAX_SCORE - PENALTY_HIGH - PENALTY_CRITICAL
        assert result.counts["high"] == 1
        assert result.counts["critical"] == 1
