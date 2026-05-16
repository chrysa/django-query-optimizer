"""Regression detection — compare a current QueryScore against a saved baseline.

Detects score regressions larger than :data:`REGRESSION_THRESHOLD` points and
persists/loads baselines as simple JSON files so they can be committed to the
repository and compared in CI.

Example::

    from django_query_optimizer.analyzers.query_analyzer import QueryAnalyzer
    from django_query_optimizer.regression.detector import RegressionDetector
    from pathlib import Path

    analyzer = QueryAnalyzer(collector.queries)
    current = analyzer.score()

    detector = RegressionDetector()
    baseline_path = Path(".query-optimizer-baseline.json")

    if baseline_path.exists():
        baseline = detector.load_baseline(baseline_path)
        result = detector.compare(baseline, current)
        if result.is_regression:
            raise SystemExit(f"Query regression detected: {result.message}")
    else:
        detector.save_baseline(current, baseline_path)
        print(f"Baseline saved: {current.summary}")

Constants
---------
``REGRESSION_THRESHOLD``
    Minimum score drop (in points) required to trigger a regression.
    A drop smaller than this is flagged in the message but does not set
    ``is_regression = True``.  Default: **5**.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from django_query_optimizer.scoring.query_scorer import QueryScore

REGRESSION_THRESHOLD: Final[int] = 5


@dataclass(frozen=True)
class RegressionResult:
    """The outcome of a baseline comparison.

    Attributes:
        is_regression: ``True`` when the score dropped by more than
            :data:`REGRESSION_THRESHOLD` points.
        score_delta:   ``current.value - baseline.value``.  Negative values
            indicate a regression.
        message:       Human-readable summary of the comparison.
    """

    is_regression: bool
    score_delta: int
    message: str


class RegressionDetector:
    """Compare a :class:`~django_query_optimizer.scoring.QueryScore` against a
    stored baseline and load/save baselines from JSON files.

    Example::

        detector = RegressionDetector()
        baseline = detector.load_baseline(Path("baseline.json"))
        result = detector.compare(baseline, current_score)
        assert not result.is_regression, result.message
    """

    def compare(self, baseline: QueryScore, current: QueryScore) -> RegressionResult:
        """Return a :class:`RegressionResult` comparing *current* to *baseline*.

        Parameters
        ----------
        baseline:
            The reference score loaded from a previous run.
        current:
            The score produced by the current run.
        """
        delta = current.value - baseline.value
        is_regression = delta < -REGRESSION_THRESHOLD
        if is_regression:
            message = (
                f"Score regressed from {baseline.value} to {current.value} "
                f"(delta={delta:+d}, threshold={-REGRESSION_THRESHOLD})"
            )
        elif delta < 0:
            message = (
                f"Score dropped slightly from {baseline.value} to {current.value} "
                f"(delta={delta:+d}) — below regression threshold of {REGRESSION_THRESHOLD}"
            )
        else:
            message = f"Score stable or improved: {baseline.value} → {current.value} (delta={delta:+d})"
        return RegressionResult(is_regression=is_regression, score_delta=delta, message=message)

    def load_baseline(self, path: Path) -> QueryScore:
        """Load a :class:`~django_query_optimizer.scoring.QueryScore` from *path*.

        The file must have been written by :meth:`save_baseline`.

        Parameters
        ----------
        path:
            Path to the JSON baseline file.

        Raises
        ------
        FileNotFoundError:
            If *path* does not exist.
        KeyError:
            If the JSON is missing required fields.
        """
        data = json.loads(path.read_text())
        return QueryScore(
            value=data["value"],
            grade=data["grade"],
            summary=data["summary"],
            counts=data["counts"],
        )

    def save_baseline(self, score: QueryScore, path: Path) -> None:
        """Persist *score* to *path* as JSON for future comparisons.

        Creates or overwrites *path*.  Parent directories must exist.

        Parameters
        ----------
        score:
            The score to persist.
        path:
            Destination file path.
        """
        path.write_text(
            json.dumps(
                {
                    "value": score.value,
                    "grade": score.grade,
                    "summary": score.summary,
                    "counts": score.counts,
                },
                indent=2,
            )
        )
