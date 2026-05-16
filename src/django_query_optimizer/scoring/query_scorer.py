"""Query health scorer.

Produces a single **health score** (0–100) that summarises the overall quality
of a set of :class:`~django_query_optimizer.recommendations.ORMRecommendation`
objects.  A perfect run with no issues returns **100**.  Each recommendation
reduces the score according to its severity.

Penalty table
-------------
+----------+--------+
| Severity | Points |
+----------+--------+
| CRITICAL |    25  |
| HIGH     |    15  |
| MEDIUM   |     8  |
| LOW      |     4  |
| INFO     |     1  |
+----------+--------+

The score is clamped to the range [0, 100].

Grade mapping
-------------
+-------+-------+
| Score | Grade |
+-------+-------+
| 90–100|   A   |
| 75–89 |   B   |
| 50–74 |   C   |
| 25–49 |   D   |
|  0–24 |   F   |
+-------+-------+

Example::

    from django_query_optimizer.scoring.query_scorer import QueryScorer
    from django_query_optimizer.recommendations.base import ORMRecommendation, Severity

    recs = [
        ORMRecommendation(issue_type="n_plus_one", severity=Severity.HIGH,
                          message="...", suggestion="..."),
        ORMRecommendation(issue_type="duplicate_query", severity=Severity.MEDIUM,
                          message="...", suggestion="..."),
    ]
    score = QueryScorer(recs).compute()
    print(score.value)   # 77
    print(score.grade)   # "B"
    print(score.summary) # "Score 77/100 (B) — 2 issue(s): 1 high, 1 medium"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from django_query_optimizer.recommendations.base import ORMRecommendation, Severity

# Penalty subtracted from 100 for each recommendation of a given severity.
PENALTY_CRITICAL: int = 25
PENALTY_HIGH: int = 15
PENALTY_MEDIUM: int = 8
PENALTY_LOW: int = 4
PENALTY_INFO: int = 1

_PENALTY_MAP: Final[dict[Severity, int]] = {
    Severity.CRITICAL: PENALTY_CRITICAL,
    Severity.HIGH: PENALTY_HIGH,
    Severity.MEDIUM: PENALTY_MEDIUM,
    Severity.LOW: PENALTY_LOW,
    Severity.INFO: PENALTY_INFO,
}

_GRADE_THRESHOLDS: Final[list[tuple[int, str]]] = [
    (90, "A"),
    (75, "B"),
    (50, "C"),
    (25, "D"),
    (0, "F"),
]

MAX_SCORE: int = 100
MIN_SCORE: int = 0


def _compute_grade(score: int) -> str:
    """Return the letter grade for *score*."""
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"  # pragma: no cover — 0 hits the last entry


@dataclass(frozen=True)
class QueryScore:
    """The result of a scoring computation.

    Attributes:
        value:   Integer health score in [0, 100].
        grade:   Letter grade (A / B / C / D / F).
        summary: Human-readable one-liner.
        counts:  Per-severity recommendation counts.
    """

    value: int
    grade: str
    summary: str
    counts: dict[str, int]


class QueryScorer:
    """Compute a health score from a list of :class:`ORMRecommendation` objects.

    Parameters
    ----------
    recommendations:
        The list produced by :meth:`~django_query_optimizer.analyzers.QueryAnalyzer.analyze`.

    Example::

        scorer = QueryScorer(recommendations)
        score = scorer.compute()
        if score.grade in ("D", "F"):
            raise RuntimeError(f"Query health too low: {score.summary}")
    """

    def __init__(self, recommendations: list[ORMRecommendation]) -> None:
        self._recommendations = recommendations

    def compute(self) -> QueryScore:
        """Compute and return the :class:`QueryScore`."""
        counts: dict[str, int] = {s.value: 0 for s in Severity}
        total_penalty = 0

        for rec in self._recommendations:
            counts[rec.severity.value] += 1
            total_penalty += _PENALTY_MAP[rec.severity]

        value = max(MIN_SCORE, MAX_SCORE - total_penalty)
        grade = _compute_grade(value)

        issue_count = len(self._recommendations)
        parts = [
            f"{counts[s.value]} {s.value}"
            for s in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO)
            if counts[s.value] > 0
        ]
        detail = ", ".join(parts) if parts else "no issues"
        summary = f"Score {value}/{MAX_SCORE} ({grade}) — {issue_count} issue(s): {detail}"

        return QueryScore(value=value, grade=grade, summary=summary, counts=counts)
