"""N+1 query detector.

Detects when the same SQL *pattern* (literals replaced with ``?``) is executed
multiple times from the same call site — the classic Django N+1 anti-pattern
that arises from iterating over a queryset and accessing related objects.

Threshold constants
-------------------
``N_PLUS_ONE_MIN_COUNT``
    Minimum number of pattern repetitions before flagging an issue.
    Default: **2**.

``N_PLUS_ONE_HIGH_COUNT``
    Pattern repetitions that escalate severity to HIGH.
    Default: **3**.

``N_PLUS_ONE_CRITICAL_COUNT``
    Pattern repetitions that escalate severity to CRITICAL.
    Default: **10**.

All constants can be monkey-patched in tests::

    import django_query_optimizer.detectors.n_plus_one as _d
    _d.N_PLUS_ONE_MIN_COUNT = 5

Example::

    from django_query_optimizer.detectors.n_plus_one import NplusOneDetector
    from django_query_optimizer.collectors.query_collector import CapturedQuery

    queries = [
        CapturedQuery(sql="SELECT * FROM book WHERE author_id = 1", duration_ms=2.0,
                      stack_trace=[], python_file="views.py", python_line=42),
        CapturedQuery(sql="SELECT * FROM book WHERE author_id = 2", duration_ms=2.0,
                      stack_trace=[], python_file="views.py", python_line=42),
    ]
    recs = NplusOneDetector().detect(queries)
    # → one MEDIUM recommendation, issue_type="n_plus_one"
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Final

from django_query_optimizer.collectors.query_collector import CapturedQuery
from django_query_optimizer.recommendations.base import ORMRecommendation, Severity

# Threshold constants — public and monkey-patchable from tests / config.
N_PLUS_ONE_MIN_COUNT: int = 2
N_PLUS_ONE_HIGH_COUNT: int = 3
N_PLUS_ONE_CRITICAL_COUNT: int = 10

# Regex that matches any SQL literal value: quoted strings, numbers, TRUE/FALSE/NULL.
_LITERAL_RE: Final[re.Pattern[str]] = re.compile(
    r"'[^']*'|\"[^\"]*\"|\b\d+\b|\b(?:TRUE|FALSE|NULL)\b",
    re.IGNORECASE,
)


def normalize_sql(sql: str) -> str:
    """Replace all literal values in *sql* with ``?`` and uppercase.

    Two queries that differ only in their WHERE clause values will produce the
    same normalised form, allowing N+1 detection across parametrised queries.

    Example::

        >>> normalize_sql("SELECT * FROM book WHERE author_id = 42")
        'SELECT * FROM BOOK WHERE AUTHOR_ID = ?'
        >>> normalize_sql("SELECT * FROM user WHERE name = 'alice'")
        'SELECT * FROM USER WHERE NAME = ?'
    """
    normalized = _LITERAL_RE.sub("?", sql)
    return " ".join(normalized.split()).upper()


class NplusOneDetector:
    """Detect N+1 query patterns in a list of captured queries.

    Groups queries by (normalised SQL, python_file, python_line).  Any group
    whose size meets or exceeds :data:`N_PLUS_ONE_MIN_COUNT` is flagged.

    Severity escalation:

    * ``>= N_PLUS_ONE_CRITICAL_COUNT`` → CRITICAL
    * ``>= N_PLUS_ONE_HIGH_COUNT``     → HIGH
    * ``>= N_PLUS_ONE_MIN_COUNT``      → MEDIUM
    """

    def detect(self, queries: list[CapturedQuery]) -> list[ORMRecommendation]:
        """Return N+1 recommendations for the given query list."""
        groups: dict[tuple[str, str, int], list[CapturedQuery]] = defaultdict(list)
        for query in queries:
            key = (normalize_sql(query.sql), query.python_file, query.python_line)
            groups[key].append(query)

        results: list[ORMRecommendation] = []
        for (normalized, py_file, py_line), group_queries in groups.items():
            count = len(group_queries)
            if count < N_PLUS_ONE_MIN_COUNT:
                continue

            severity: Severity
            if count >= N_PLUS_ONE_CRITICAL_COUNT:
                severity = Severity.CRITICAL
            elif count >= N_PLUS_ONE_HIGH_COUNT:
                severity = Severity.HIGH
            else:
                severity = Severity.MEDIUM

            results.append(
                ORMRecommendation(
                    issue_type="n_plus_one",
                    severity=severity,
                    message=(f"Potential N+1: query pattern executed {count} times: {normalized[:80]}"),
                    suggestion=(
                        "Use select_related() for ForeignKey/OneToOne traversals "
                        "or prefetch_related() for reverse/M2M relations to batch "
                        "queries into a single JOIN or IN lookup."
                    ),
                    python_file=py_file,
                    python_line=py_line,
                )
            )

        return results
