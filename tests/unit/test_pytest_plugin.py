"""Tests for pytest_plugin assertion helpers.

We test the internal ``_NoQueryAssertion``, ``_MaxQueryAssertion``, and
``_QueryHealthAssertion`` classes directly, constructing lightweight stubs for
``QueryCollector`` so no real DB connection is required.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_mock import MockerFixture

from django_query_optimizer.testing.pytest_plugin import (
    _MaxQueryAssertion,
    _NoQueryAssertion,
    _QueryHealthAssertion,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _collector(mocker: MockerFixture, count: int) -> Any:
    """Return a mock QueryCollector with *count* fake queries."""
    col = mocker.MagicMock()
    col.count = count
    col.queries = [mocker.MagicMock(sql=f"SELECT {i}") for i in range(count)]
    return col


# ── _NoQueryAssertion ─────────────────────────────────────────────────────────


class TestNoQueryAssertion:
    def test_passes_when_no_queries(self, mocker: MockerFixture) -> None:
        checker = _NoQueryAssertion(_collector(mocker, 0))
        checker()  # must not raise

    def test_fails_when_one_query(self, mocker: MockerFixture) -> None:
        checker = _NoQueryAssertion(_collector(mocker, 1))
        with pytest.raises(AssertionError, match="1 were executed"):
            checker()

    def test_fails_when_multiple_queries(self, mocker: MockerFixture) -> None:
        checker = _NoQueryAssertion(_collector(mocker, 5))
        with pytest.raises(AssertionError, match="5 were executed"):
            checker()

    def test_error_message_contains_sql(self, mocker: MockerFixture) -> None:
        col = _collector(mocker, 1)
        col.queries[0].sql = "SELECT id FROM auth_user"
        checker = _NoQueryAssertion(col)
        with pytest.raises(AssertionError, match="SELECT id FROM auth_user"):
            checker()

    def test_error_message_contains_query_count(self, mocker: MockerFixture) -> None:
        checker = _NoQueryAssertion(_collector(mocker, 3))
        with pytest.raises(AssertionError, match="3"):
            checker()

    def test_error_message_lists_query_index(self, mocker: MockerFixture) -> None:
        checker = _NoQueryAssertion(_collector(mocker, 2))
        with pytest.raises(AssertionError, match=r"\[1\]"):
            checker()

    def test_sql_is_truncated_at_120_chars(self, mocker: MockerFixture) -> None:
        long_sql = "SELECT " + "x" * 200
        col = _collector(mocker, 0)
        col.count = 1
        col.queries = [mocker.MagicMock(sql=long_sql)]
        checker = _NoQueryAssertion(col)
        with pytest.raises(AssertionError) as exc_info:
            checker()
        # The captured message must not contain the full 200-char SQL
        assert long_sql not in str(exc_info.value)


# ── _MaxQueryAssertion ────────────────────────────────────────────────────────


class TestMaxQueryAssertion:
    def test_passes_when_exactly_at_limit(self, mocker: MockerFixture) -> None:
        checker = _MaxQueryAssertion(_collector(mocker, 3))
        checker(3)  # must not raise

    def test_passes_when_below_limit(self, mocker: MockerFixture) -> None:
        checker = _MaxQueryAssertion(_collector(mocker, 1))
        checker(5)  # must not raise

    def test_passes_when_zero_queries_and_zero_limit(self, mocker: MockerFixture) -> None:
        checker = _MaxQueryAssertion(_collector(mocker, 0))
        checker(0)  # must not raise

    def test_fails_when_over_limit(self, mocker: MockerFixture) -> None:
        checker = _MaxQueryAssertion(_collector(mocker, 4))
        with pytest.raises(AssertionError, match="4"):
            checker(2)

    def test_error_message_contains_limit(self, mocker: MockerFixture) -> None:
        checker = _MaxQueryAssertion(_collector(mocker, 5))
        with pytest.raises(AssertionError, match="3"):
            checker(3)

    def test_singular_grammar_for_one(self, mocker: MockerFixture) -> None:
        checker = _MaxQueryAssertion(_collector(mocker, 2))
        with pytest.raises(AssertionError, match="1 SQL query"):
            checker(1)

    def test_plural_grammar_for_multiple(self, mocker: MockerFixture) -> None:
        checker = _MaxQueryAssertion(_collector(mocker, 5))
        with pytest.raises(AssertionError, match="queries"):
            checker(3)

    def test_fails_when_one_over_zero_limit(self, mocker: MockerFixture) -> None:
        checker = _MaxQueryAssertion(_collector(mocker, 1))
        with pytest.raises(AssertionError):
            checker(0)


# ── _QueryHealthAssertion ─────────────────────────────────────────────────────


class TestQueryHealthAssertion:
    def _make_checker(self, mocker: MockerFixture, count: int = 0) -> _QueryHealthAssertion:
        return _QueryHealthAssertion(_collector(mocker, count))

    def test_passes_when_score_equals_threshold(self, mocker: MockerFixture) -> None:
        checker = self._make_checker(mocker, 0)
        # 0 queries → score 100/100 → passes any threshold
        score = checker(min_score=100)
        assert score.value == 100

    def test_passes_when_score_above_threshold(self, mocker: MockerFixture) -> None:
        checker = self._make_checker(mocker, 0)
        score = checker(min_score=80)
        assert score.value >= 80

    def test_returns_query_score(self, mocker: MockerFixture) -> None:
        checker = self._make_checker(mocker, 0)
        from django_query_optimizer.scoring.query_scorer import QueryScore

        score = checker()
        assert isinstance(score, QueryScore)

    def test_default_threshold_is_80(self, mocker: MockerFixture) -> None:
        """Default min_score=80 should pass when there are no issues."""
        checker = self._make_checker(mocker, 0)
        score = checker()  # default min_score=80
        assert score.value >= 80

    def test_fails_when_score_below_threshold(self, mocker: MockerFixture) -> None:
        """Patch scorer to return a low score; assert AssertionError is raised."""
        from django_query_optimizer.scoring.query_scorer import QueryScore

        low_score = QueryScore(
            value=40,
            grade="D",
            summary="Score 40/100 (D) — 4 issue(s): 4 high",
            counts={"critical": 0, "high": 4, "medium": 0, "low": 0, "info": 0},
        )
        checker = self._make_checker(mocker, 0)
        mocker.patch(
            "django_query_optimizer.scoring.query_scorer.QueryScorer.compute",
            return_value=low_score,
        )
        with pytest.raises(AssertionError, match="40"):
            checker(min_score=80)

    def test_error_message_contains_score(self, mocker: MockerFixture) -> None:
        from django_query_optimizer.scoring.query_scorer import QueryScore

        low_score = QueryScore(
            value=50,
            grade="C",
            summary="Score 50/100 (C) — 2 issue(s)",
            counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        )
        checker = self._make_checker(mocker, 0)
        mocker.patch(
            "django_query_optimizer.scoring.query_scorer.QueryScorer.compute",
            return_value=low_score,
        )
        with pytest.raises(AssertionError, match="50"):
            checker(min_score=80)

    def test_error_message_contains_grade(self, mocker: MockerFixture) -> None:
        from django_query_optimizer.scoring.query_scorer import QueryScore

        low_score = QueryScore(
            value=50,
            grade="C",
            summary="Score 50/100 (C) — 2 issue(s)",
            counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        )
        checker = self._make_checker(mocker, 0)
        mocker.patch(
            "django_query_optimizer.scoring.query_scorer.QueryScorer.compute",
            return_value=low_score,
        )
        with pytest.raises(AssertionError, match=r"\bC\b"):
            checker(min_score=80)

    def test_error_message_contains_threshold(self, mocker: MockerFixture) -> None:
        from django_query_optimizer.scoring.query_scorer import QueryScore

        low_score = QueryScore(
            value=60,
            grade="C",
            summary="Score 60/100 (C)",
            counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        )
        checker = self._make_checker(mocker, 0)
        mocker.patch(
            "django_query_optimizer.scoring.query_scorer.QueryScorer.compute",
            return_value=low_score,
        )
        with pytest.raises(AssertionError, match="90"):
            checker(min_score=90)

    def test_passes_with_custom_low_threshold(self, mocker: MockerFixture) -> None:
        """A score of 50 should pass when threshold is 40."""
        from django_query_optimizer.scoring.query_scorer import QueryScore

        medium_score = QueryScore(
            value=50,
            grade="C",
            summary="Score 50/100 (C)",
            counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        )
        checker = self._make_checker(mocker, 0)
        mocker.patch(
            "django_query_optimizer.scoring.query_scorer.QueryScorer.compute",
            return_value=medium_score,
        )
        score = checker(min_score=40)
        assert score.value == 50
