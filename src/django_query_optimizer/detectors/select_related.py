"""select_related / prefetch_related suggestion detector.

Detects foreign-key traversal patterns that can be eliminated by adding
``select_related()`` (single-object FK) or ``prefetch_related()``
(reverse FK / M2M) to a queryset.

Detection logic
---------------
A SQL query of the form ``SELECT … FROM <table> WHERE <pk_col> = ?`` executed
more than once from the **same call-site** indicates that the application is
loading related objects one by one instead of joining them in a single query.

The detector identifies the *accessed table* from the FROM clause and suggests
the snake_case field name as a hint to pass to ``select_related()`` or
``prefetch_related()``.

Threshold constants
-------------------
``SELECT_RELATED_MIN_COUNT``
    Minimum number of pattern repetitions before flagging an issue.
    Default: **2**.

All constants can be monkey-patched in tests::

    import django_query_optimizer.detectors.select_related as _d
    _d.SELECT_RELATED_MIN_COUNT = 3

Example::

    from django_query_optimizer.detectors.select_related import SelectRelatedDetector

    recs = SelectRelatedDetector().detect(queries)
    for rec in recs:
        print(rec.suggestion)  # "Add select_related('author') to your queryset."
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Final

from django_query_optimizer.collectors.query_collector import CapturedQuery
from django_query_optimizer.recommendations.base import ORMRecommendation, Severity

# Minimum count of FK-lookup repetitions before flagging
SELECT_RELATED_MIN_COUNT: int = 2

# Matches: SELECT … FROM <table> WHERE <col> = ? (normalised SQL)
# We capture <table> and <col> to identify the related model and PK column.
_FK_LOOKUP_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    ^SELECT\s+.+?\s+FROM\s+                     # SELECT … FROM
    (?:"?(?P<schema>[A-Z0-9_]+)"?\.)? # optional schema
    "?(?P<table>[A-Z0-9_]+)"?                    # table name
    \s+WHERE\s+
    "?(?P<col>[A-Z0-9_]+)"?\s*=\s*\?            # WHERE col = ?
    \s*$                                          # nothing after
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _looks_like_fk_lookup(sql: str) -> re.Match[str] | None:
    """Return the regex match if *sql* looks like a single-row FK lookup."""
    return _FK_LOOKUP_RE.match(sql.strip())


def _table_to_field(table: str) -> str:
    """Convert a DB table name to a likely Django field name.

    Strips a common ``app_`` prefix pattern and lowercases.
    Examples:
        ``MYAPP_AUTHOR``   → ``author``
        ``AUTH_USER``      → ``auth_user``  (ambiguous — keep full)
        ``BOOK``           → ``book``
    """
    lower = table.lower()
    # Strip a single «app_» prefix segment if the result is a single word.
    parts = lower.split("_", 1)
    if len(parts) == 2 and parts[1] and "_" not in parts[1]:
        return parts[1]
    return lower


class SelectRelatedDetector:
    """Detect missing ``select_related`` / ``prefetch_related`` calls.

    Each group of FK-lookup repetitions from the same call-site produces one
    :class:`~django_query_optimizer.recommendations.ORMRecommendation` with
    severity **MEDIUM** (becomes **HIGH** when count ≥ 10).

    Example::

        queries = [
            CapturedQuery(sql="SELECT * FROM book_author WHERE id = 1", ...),
            CapturedQuery(sql="SELECT * FROM book_author WHERE id = 2", ...),
        ]
        recs = SelectRelatedDetector().detect(queries)
        assert recs[0].issue_type == "missing_select_related"
    """

    def detect(self, queries: list[CapturedQuery]) -> list[ORMRecommendation]:
        """Analyse *queries* and return FK traversal recommendations."""
        from django_query_optimizer.detectors.n_plus_one import normalize_sql

        # Group by (normalised_sql, call_site)
        groups: dict[tuple[str, str, int], list[CapturedQuery]] = defaultdict(list)
        for query in queries:
            normalised = normalize_sql(query.sql)
            if _looks_like_fk_lookup(normalised):
                key = (normalised, query.python_file, query.python_line)
                groups[key].append(query)

        recommendations: list[ORMRecommendation] = []
        for (normalised_sql, python_file, python_line), group in groups.items():
            count = len(group)
            if count < SELECT_RELATED_MIN_COUNT:
                continue

            match = _looks_like_fk_lookup(normalised_sql)
            if match is None:  # pragma: no cover — filtered above
                continue
            table = match.group("table")
            field_hint = _table_to_field(table)

            severity = Severity.HIGH if count >= 10 else Severity.MEDIUM
            recommendations.append(
                ORMRecommendation(
                    issue_type="missing_select_related",
                    severity=severity,
                    message=(
                        f"Foreign-key lookup on '{table}' executed {count} times "
                        f"from the same call-site — likely a missing "
                        f"select_related() / prefetch_related()."
                    ),
                    suggestion=(
                        f"Add select_related('{field_hint}') (or "
                        f"prefetch_related('{field_hint}')) to your queryset "
                        f"to fetch related objects in a single query."
                    ),
                    python_file=python_file,
                    python_line=python_line,
                )
            )
        return recommendations
