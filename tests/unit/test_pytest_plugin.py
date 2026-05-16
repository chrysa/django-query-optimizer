"""Tests for pytest_plugin assertion helpers.

We test the internal ``_NoQueryAssertion``, ``_MaxQueryAssertion``, and
``_QueryHealthAssertion`` classes directly, constructing lightweight stubs for
``QueryCollector`` so no real DB connection is required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from django_query_optimizer.testing.pytest_plugin import (
    _MaxQueryAssertion,
    _NoQueryAssertion,
    _QueryHealthAssertion,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _collector(count: int) -> MagicMock:
    """Return a mock QueryCollector with *count* fake queries."""
    col = MagicMock()
    col.count = count
    col.queries = [MagicMock(sql=f"SELECT {i}") for i in range(count)]
    return col


# ── _NoQueryAssertion ─────────────────────────────────────────────────────────


class TestNoQueryAssertion:
    def test_passes_when_no_queries(self) -> None:
        checker = _NoQueryAssertion(_collector(0))
        checker()  # must not raise

    def test_fails_when_one_query(self) -> None:
        checker = _NoQueryAssertion(_collector(1))
        with pytest.raises(AssertionError, match="1 were executed"):
            checker()

    def test_fails_when_multiple_queries(self) -> None:
        checker = _NoQueryAssertion(_collector(5))
        with pytest.raises(AssertionError, match="5 were executed"):
            checker()

    def test_error_message_contains_sql(self) -> None:
        col = _collector(1)
        col.queries[0].sql = "SELECT id FROM auth_user"
        checker = _NoQueryAssertion(col)
        with pytest.raises(AssertionError, match="SELECT id FROM auth_user"):
            checker()

    def test_error_message_contains_query_count(self) -> None:
        checker = _NoQueryAssertion(_collector(3))
        with pytest.raises(AssertionError, match="3"):
            checker()

    def test_error_message_lists_query_index(self) -> None:
        checker = _NoQueryAssertion(_collector(2))
        with pytest.raises(AssertionError, match=r"\[1\]"):
            checker()

    def test_sql_is_truncated_at_120_chars(self) -> None:
        long_sql = "SELECT " + "x" * 200
        col = _collector(0)
        col.count = 1
        col.queries = [MagicMock(sql=long_sql)]
        checker = _NoQueryAssertion(col)
        with pytest.raises(AssertionError) as exc_info:
            checker()
        # The captured message must not contain the full 200-char SQL
        assert long_sql not in str(exc_info.value)


# ── _MaxQueryAssertion ────────────────────────────────────────────────────────


class TestMaxQueryAssertion:
    def test_passes_when_exactly_at_limit(self) -> None:
        checker = _MaxQueryAssertion(_collector(3))
        checker(3)  # must not raise

    def test_passes_when_below_limit(self) -> None:
        checker = _MaxQueryAssertion(_collector(1))
        checker(5)  # must not raise

    def test_passes_when_zero_queries_and_zero_limit(self) -> None:
        checker = _MaxQueryAssertion(_collector(0))
        checker(0)  # must not raise

    def test_fails_when_over_limit(self) -> None:
        checker = _MaxQueryAssertion(_collector(4))
        with pytest.raises(AssertionError, match="4"):
            checker(2)

    def test_error_message_contains_limit(self) -> None:
        checker = _MaxQueryAssertion(_collector(5))
        with pytest.raises(AssertionError, match="3"):
            checker(3)

    def test_singular_grammar_for_one(self) -> None:
        checker = _MaxQueryAssertion(_collector(2))
        with pytest.raises(AssertionError, match="1 SQL query"):
            checker(1)

    def test_plural_grammar_for_multiple(self) -> None:
        checker = _MaxQueryAssertion(_collector(5))
        with pytest.raises(AssertionError, match="queries"):
            checker(3)

    def test_fails_when_one_over_zero_limit(self) -> None:
        checker = _MaxQueryAssertion(_collector(1))
        with pytest.raises(AssertionError):
            checker(0)


# ── _QueryHealthAssertion ─────────────────────────────────────────────────────


class TestQueryHealthAssertion:
    def _make_checker(self, count: int = 0) -> _QueryHealthAssertion:
        return _QueryHealthAssertion(_collector(count))

    def test_passes_when_score_equals_threshold(self) -> None:
        checker = self._make_checker(0)
        # 0 queries → score 100/100 → passes any threshold
        score = checker(min_score=100)
        assert score.value == 100

    def test_passes_when_score_above_threshold(self) -> None:
        checker = self._make_checker(0)
        score = checker(min_score=80)
        assert score.value >= 80

    def test_returns_query_score(self) -> None:
        checker = self._make_checker(0)
        from django_query_optimizer.scoring.query_scorer import QueryScore

        score = checker()
        assert isinstance(score, QueryScore)

    def test_default_threshold_is_80(self) -> None:
        """Default min_score=80 should pass when there are no issues."""
        checker = self._make_checker(0)
        score = checker()  # default min_score=80
        assert score.value >= 80

    def test_fails_when_score_below_threshold(self) -> None:
        """Patch scorer to return a low score; assert AssertionError is raised."""
        from django_query_optimizer.scoring.query_scorer import QueryScore

        low_score = QueryScore(
            value=40,
            grade="D",
            summary="Score 40/100 (D) — 4 issue(s): 4 high",
            counts={"critical": 0, "high": 4, "medium": 0, "low": 0, "info": 0},
        )
        checker = self._make_checker(0)
        with (
            patch(
                "django_query_optimizer.scoring.query_scorer.QueryScorer.compute",
                return_value=low_score,
            ),
            pytest.raises(AssertionError, match="40"),
        ):
            checker(min_score=80)

    def test_error_message_contains_score(self) -> None:
        from django_query_optimizer.scoring.query_scorer import QueryScore

        low_score = QueryScore(
            value=50,
            grade="C",
            summary="Score 50/100 (C) — 2 issue(s)",
            counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        )
        checker = self._make_checker(0)
        with (
            patch(
                "django_query_optimizer.scoring.query_scorer.QueryScorer.compute",
                return_value=low_score,
            ),
            pytest.raises(AssertionError, match="50"),
        ):
            checker(min_score=80)

    def test_error_message_contains_grade(self) -> None:
        from django_query_optimizer.scoring.query_scorer import QueryScore

        low_score = QueryScore(
            value=50,
            grade="C",
            summary="Score 50/100 (C) — 2 issue(s)",
            counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        )
        checker = self._make_checker(0)
        with (
            patch(
                "django_query_optimizer.scoring.query_scorer.QueryScorer.compute",
                return_value=low_score,
            ),
            pytest.raises(AssertionError, match=r"\bC\b"),
        ):
            checker(min_score=80)

    def test_error_message_contains_threshold(self) -> None:
        from django_query_optimizer.scoring.query_scorer import QueryScore

        low_score = QueryScore(
            value=60,
            grade="C",
            summary="Score 60/100 (C)",
            counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        )
        checker = self._make_checker(0)
        with (
            patch(
                "django_query_optimizer.scoring.query_scorer.QueryScorer.compute",
                return_value=low_score,
            ),
            pytest.raises(AssertionError, match="90"),
        ):
            checker(min_score=90)

    def test_passes_with_custom_low_threshold(self) -> None:
        """A score of 50 should pass when threshold is 40."""
        from django_query_optimizer.scoring.query_scorer import QueryScore

        medium_score = QueryScore(
            value=50,
            grade="C",
            summary="Score 50/100 (C)",
            counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        )
        checker = self._make_checker(0)
        with patch(
            "django_query_optimizer.scoring.query_scorer.QueryScorer.compute",
            return_value=medium_score,
        ):
            score = checker(min_score=40)
            assert score.value == 50
