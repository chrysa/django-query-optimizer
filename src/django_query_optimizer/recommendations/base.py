"""Base recommendation data class.

This module defines the two core types that consumers of
``django-query-optimizer`` interact with after analysis:

``Severity``
    A ``StrEnum`` that ranks how urgent an ORM issue is, from ``CRITICAL``
    (must fix before deploy) down to ``INFO`` (nice-to-have).
    ``StrEnum`` membership lets you compare and serialize values naturally:
    ``rec.severity == "high"``.

``ORMRecommendation``
    A **frozen** dataclass representing a single detected issue.  Frozen means
    instances are hashable and can be stored in sets or used as dict keys.
    Instances support ``<`` comparison so a plain ``sorted()`` returns them
    ordered from most to least severe.

Example::

    from django_query_optimizer.recommendations.base import ORMRecommendation, Severity

    rec = ORMRecommendation(
        issue_type="slow_query",
        severity=Severity.HIGH,
        message="Query took 142.3 ms (threshold: 100 ms)",
        suggestion="Add an index on the filtered column.",
        python_file="views/orders.py",
        python_line=47,
    )
    print(rec.severity)          # "high"
    print(rec.severity == "high") # True
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class Severity(StrEnum):
    """Severity level of a detected ORM issue."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


_SEVERITY_ORDER: Final[dict[Severity, int]] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


@dataclass(frozen=True)
class ORMRecommendation:
    """A single optimization recommendation produced by the analyzer.

    Attributes:
        issue_type: Short identifier such as ``"n_plus_1"`` or ``"missing_index"``.
        severity: How urgent the fix is.
        message: Human-readable description of the problem.
        suggestion: Concrete ORM code to apply.
        python_file: Source file where the issue originates (best-effort).
        python_line: Line number in *python_file* (0 = unknown).
    """

    issue_type: str
    severity: Severity
    message: str
    suggestion: str
    python_file: str = ""
    python_line: int = 0

    def __lt__(self, other: ORMRecommendation) -> bool:
        return _SEVERITY_ORDER[self.severity] < _SEVERITY_ORDER[other.severity]
