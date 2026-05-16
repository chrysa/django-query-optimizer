"""Django REST Framework serializer N+1 detector.

Detects N+1 query patterns that originate from DRF serializer code, providing
DRF-specific suggestions to add ``select_related()`` or ``prefetch_related()``
in the corresponding ViewSet's ``get_queryset()`` method.

Detection logic
---------------
1. For each captured query, scan its ``stack_trace`` for frames belonging to
   DRF serializer/relation/field modules.
2. Extract the outermost *user-code* frame that appears immediately before the
   DRF frame, so we can point to the serializer definition.
3. Normalise the SQL (replacing literals with ``?``) then group queries by
   ``(normalised_sql, user_file, user_line)``.
4. Groups with ``count >= DRF_SERIALIZER_MIN_COUNT`` are flagged.

This detector complements :class:`~django_query_optimizer.detectors.n_plus_one.NplusOneDetector`
by providing DRF-specific context and remediation advice instead of generic ORM
suggestions.

Threshold constants
-------------------
``DRF_SERIALIZER_MIN_COUNT``
    Minimum number of pattern repetitions before flagging an issue.
    Default: **2**.

``DRF_SERIALIZER_HIGH_COUNT``
    Repetitions that escalate severity from MEDIUM to HIGH.
    Default: **5**.

All constants can be monkey-patched in tests::

    import django_query_optimizer.detectors.drf_serializer as _d
    _d.DRF_SERIALIZER_MIN_COUNT = 3

Example::

    from django_query_optimizer.detectors.drf_serializer import DRFSerializerDetector
    from django_query_optimizer.collectors.query_collector import CapturedQuery

    # Stack trace contains a DRF serializer frame
    queries = [
        CapturedQuery(
            sql="SELECT * FROM api_author WHERE id = 1",
            duration_ms=2.0,
            stack_trace=[
                '  File "site-packages/rest_framework/serializers.py", line 500, '
                'in to_representation\\n    fields = self._readable_fields\\n',
                '  File "myapp/serializers.py", line 20, in to_representation\\n'
                '    return super().to_representation(instance)\\n',
            ],
            python_file="myapp/serializers.py",
            python_line=20,
        ),
        CapturedQuery(
            sql="SELECT * FROM api_author WHERE id = 2",
            duration_ms=2.0,
            stack_trace=[
                '  File "site-packages/rest_framework/serializers.py", line 500, '
                'in to_representation\\n    fields = self._readable_fields\\n',
                '  File "myapp/serializers.py", line 20, in to_representation\\n'
                '    return super().to_representation(instance)\\n',
            ],
            python_file="myapp/serializers.py",
            python_line=20,
        ),
    ]
    recs = DRFSerializerDetector().detect(queries)
    # → one MEDIUM recommendation, issue_type="drf_n_plus_one"
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Final

from django_query_optimizer.collectors.query_collector import CapturedQuery
from django_query_optimizer.detectors.n_plus_one import normalize_sql
from django_query_optimizer.recommendations.base import ORMRecommendation, Severity

# Threshold constants — public and monkey-patchable.
DRF_SERIALIZER_MIN_COUNT: int = 2
DRF_SERIALIZER_HIGH_COUNT: int = 5

# Path fragments that identify a stack frame as belonging to DRF internals.
_DRF_FRAME_SIGNATURES: Final[tuple[str, ...]] = (
    "rest_framework/serializers",
    "rest_framework\\serializers",
    "rest_framework/relations",
    "rest_framework\\relations",
    "rest_framework/fields",
    "rest_framework\\fields",
)

# Regex to extract file path and line number from a formatted stack frame.
# Frame format (from traceback.format_stack):
#   '  File "/path/to/file.py", line N, in func_name\n    code\n'
_FRAME_RE: Final[re.Pattern[str]] = re.compile(r'File "(?P<path>[^"]+)", line (?P<lineno>\d+)')


def _is_drf_frame(frame: str) -> bool:
    """Return True if *frame* originates from DRF serializer/relations/fields."""
    return any(sig in frame for sig in _DRF_FRAME_SIGNATURES)


def _extract_frame_location(frame: str) -> tuple[str, int]:
    """Return ``(filepath, lineno)`` parsed from a formatted stack frame string."""
    match = _FRAME_RE.search(frame)
    if match:
        return match.group("path"), int(match.group("lineno"))
    return "", 0


def _find_drf_call_site(stack_trace: list[str]) -> tuple[str, int]:
    """Return the user-code call-site that invoked a DRF serializer method.

    Scans the stack frames (as returned by ``traceback.format_stack()``) and
    returns the ``(file, line)`` of the last non-DRF frame that appears before
    the first DRF frame.  This points to the serializer subclass or viewset
    that triggered the query.

    Returns ``("", 0)`` when no DRF frame is found in the trace.
    """
    first_drf_idx: int | None = None
    for idx, frame in enumerate(stack_trace):
        if _is_drf_frame(frame):
            first_drf_idx = idx
            break

    if first_drf_idx is None:
        return "", 0

    # Walk backwards from the DRF frame to find the closest user-code frame.
    for frame in reversed(stack_trace[:first_drf_idx]):
        path, lineno = _extract_frame_location(frame)
        if path and not any(sig in path for sig in _DRF_FRAME_SIGNATURES):
            return path, lineno

    # Fallback: use the DRF frame itself.
    return _extract_frame_location(stack_trace[first_drf_idx])


def _has_drf_frame(stack_trace: list[str]) -> bool:
    """Return True if any frame in *stack_trace* belongs to DRF."""
    return any(_is_drf_frame(frame) for frame in stack_trace)


class DRFSerializerDetector:
    """Detect N+1 query patterns triggered by DRF serializer methods.

    Queries that pass through DRF serializer/field/relation code and repeat
    the same SQL pattern from the same call-site are flagged with DRF-specific
    remediation advice.

    Severity escalation:

    * ``>= DRF_SERIALIZER_HIGH_COUNT`` → HIGH
    * ``>= DRF_SERIALIZER_MIN_COUNT`` → MEDIUM
    """

    def detect(self, queries: list[CapturedQuery]) -> list[ORMRecommendation]:
        """Return DRF serializer N+1 recommendations for the given query list."""
        # Filter to only queries that pass through DRF code.
        drf_queries = [q for q in queries if _has_drf_frame(q.stack_trace)]
        if not drf_queries:
            return []

        groups: dict[tuple[str, str, int], list[CapturedQuery]] = defaultdict(list)
        for query in drf_queries:
            call_file, call_line = _find_drf_call_site(query.stack_trace)
            # Fall back to the query's own python_file/line if no DRF frame
            # yielded a call-site (e.g. stack trace was truncated).
            if not call_file:
                call_file = query.python_file
                call_line = query.python_line
            key = (normalize_sql(query.sql), call_file, call_line)
            groups[key].append(query)

        results: list[ORMRecommendation] = []
        for (normalized, py_file, py_line), group_queries in groups.items():
            count = len(group_queries)
            if count < DRF_SERIALIZER_MIN_COUNT:
                continue

            severity = Severity.HIGH if count >= DRF_SERIALIZER_HIGH_COUNT else Severity.MEDIUM

            results.append(
                ORMRecommendation(
                    issue_type="drf_n_plus_one",
                    severity=severity,
                    message=(f"DRF serializer triggered {count} repeated queries: {normalized[:80]}"),
                    suggestion=(
                        "Add select_related() or prefetch_related() to your "
                        "ViewSet's get_queryset() to pre-fetch the related objects "
                        "accessed by the serializer fields."
                    ),
                    python_file=py_file,
                    python_line=py_line,
                )
            )

        return results
