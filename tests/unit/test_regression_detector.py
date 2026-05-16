"""Tests for RegressionDetector and RegressionResult."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from django_query_optimizer.regression.detector import (
    REGRESSION_THRESHOLD,
    RegressionDetector,
    RegressionResult,
)
from django_query_optimizer.scoring.query_scorer import QueryScore

# ── Helpers ───────────────────────────────────────────────────────────────────


def _score(value: int = 80, grade: str = "B") -> QueryScore:
    return QueryScore(
        value=value,
        grade=grade,
        summary=f"Score {value}/100 ({grade})",
        counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
    )


# ── RegressionResult ──────────────────────────────────────────────────────────


class TestRegressionResultIsFrozen:
    def test_frozen(self) -> None:
        result = RegressionResult(is_regression=False, score_delta=0, message="ok")
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            result.is_regression = True  # type: ignore[misc]


# ── RegressionDetector.compare ────────────────────────────────────────────────


class TestCompareNoRegression:
    def test_same_score_is_not_regression(self) -> None:
        det = RegressionDetector()
        result = det.compare(_score(80), _score(80))
        assert not result.is_regression

    def test_improved_score_is_not_regression(self) -> None:
        det = RegressionDetector()
        result = det.compare(_score(70), _score(90))
        assert not result.is_regression

    def test_improved_delta_is_positive(self) -> None:
        det = RegressionDetector()
        result = det.compare(_score(70), _score(90))
        assert result.score_delta == 20

    def test_same_score_delta_is_zero(self) -> None:
        det = RegressionDetector()
        result = det.compare(_score(80), _score(80))
        assert result.score_delta == 0

    def test_small_drop_below_threshold_not_regression(self) -> None:
        # Drop of exactly REGRESSION_THRESHOLD is NOT a regression (strict <)
        det = RegressionDetector()
        result = det.compare(_score(80), _score(80 - REGRESSION_THRESHOLD))
        assert not result.is_regression

    def test_small_drop_message_mentions_below_threshold(self) -> None:
        det = RegressionDetector()
        result = det.compare(_score(80), _score(77))
        assert not result.is_regression
        assert "below" in result.message.lower() or "slightly" in result.message.lower()


class TestCompareRegression:
    def test_large_drop_is_regression(self) -> None:
        det = RegressionDetector()
        result = det.compare(_score(80), _score(70))  # drop of 10 > threshold 5
        assert result.is_regression

    def test_regression_delta_is_negative(self) -> None:
        det = RegressionDetector()
        result = det.compare(_score(80), _score(70))
        assert result.score_delta == -10

    def test_regression_message_contains_scores(self) -> None:
        det = RegressionDetector()
        result = det.compare(_score(80), _score(60))
        assert "80" in result.message
        assert "60" in result.message

    def test_regression_message_contains_delta(self) -> None:
        det = RegressionDetector()
        result = det.compare(_score(80), _score(60))
        assert "-20" in result.message

    def test_no_regression_message_contains_both_scores(self) -> None:
        det = RegressionDetector()
        result = det.compare(_score(70), _score(85))
        assert "70" in result.message
        assert "85" in result.message


# ── RegressionDetector.save_baseline / load_baseline ─────────────────────────


class TestSaveLoadBaseline:
    def test_round_trip_value(self, tmp_path: Path) -> None:
        det = RegressionDetector()
        score = _score(75, "B")
        p = tmp_path / "baseline.json"
        det.save_baseline(score, p)
        loaded = det.load_baseline(p)
        assert loaded.value == 75

    def test_round_trip_grade(self, tmp_path: Path) -> None:
        det = RegressionDetector()
        score = _score(75, "B")
        p = tmp_path / "baseline.json"
        det.save_baseline(score, p)
        loaded = det.load_baseline(p)
        assert loaded.grade == "B"

    def test_round_trip_summary(self, tmp_path: Path) -> None:
        det = RegressionDetector()
        score = _score(90, "A")
        p = tmp_path / "baseline.json"
        det.save_baseline(score, p)
        loaded = det.load_baseline(p)
        assert loaded.summary == score.summary

    def test_round_trip_counts(self, tmp_path: Path) -> None:
        det = RegressionDetector()
        score = QueryScore(
            value=60,
            grade="C",
            summary="Score 60/100 (C)",
            counts={"critical": 0, "high": 2, "medium": 1, "low": 0, "info": 3},
        )
        p = tmp_path / "baseline.json"
        det.save_baseline(score, p)
        loaded = det.load_baseline(p)
        assert loaded.counts["high"] == 2
        assert loaded.counts["info"] == 3

    def test_file_is_valid_json(self, tmp_path: Path) -> None:
        det = RegressionDetector()
        p = tmp_path / "b.json"
        det.save_baseline(_score(80), p)
        data = json.loads(p.read_text())
        assert "value" in data
        assert "grade" in data
        assert "counts" in data

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        det = RegressionDetector()
        with pytest.raises(FileNotFoundError):
            det.load_baseline(tmp_path / "nonexistent.json")

    def test_overwrite_baseline(self, tmp_path: Path) -> None:
        det = RegressionDetector()
        p = tmp_path / "b.json"
        det.save_baseline(_score(80), p)
        det.save_baseline(_score(95, "A"), p)
        loaded = det.load_baseline(p)
        assert loaded.value == 95


# ── Integration: save, load, compare ─────────────────────────────────────────


class TestIntegration:
    def test_save_then_compare_stable(self, tmp_path: Path) -> None:
        det = RegressionDetector()
        p = tmp_path / "baseline.json"
        det.save_baseline(_score(80), p)
        current = _score(82)
        result = det.compare(det.load_baseline(p), current)
        assert not result.is_regression

    def test_save_then_compare_regression(self, tmp_path: Path) -> None:
        det = RegressionDetector()
        p = tmp_path / "baseline.json"
        det.save_baseline(_score(80), p)
        current = _score(65)
        result = det.compare(det.load_baseline(p), current)
        assert result.is_regression
