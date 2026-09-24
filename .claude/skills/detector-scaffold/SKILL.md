---
name: detector-scaffold
description: 'Use when adding a new ORM anti-pattern detector to django_query_optimizer/detectors/. Scaffolds the detector class, its BaseDetector-conformant test, and reminds of the export/README/CLAUDE.md updates from the "Adding a New Detector" recipe.'
---

# Detector scaffold

## When to invoke
Auto-invoke when: creating a new file under `src/django_query_optimizer/detectors/`,
or when asked to add/implement a new detector (N+1, missing index, slow query, etc.).

## The 5-step recipe (CLAUDE.md — "Adding a New Detector")

1. Create `src/django_query_optimizer/detectors/<name>.py` implementing
   `detect(queries) -> list[ORMRecommendation]` per `detectors/base.py`'s `BaseDetector`.
2. Export the class from `detectors/__init__.py` (and top-level `__init__.py` if part
   of the public API) and add it to `__all__`.
3. Write a matching test class in `tests/unit/test_<name>_detector.py`.
4. Update the detector table in `README.md` and in `CLAUDE.md`.
5. Reuse an existing `Severity` level (`recommendations/base.py`) or extend the enum
   with justification — do not invent an ad-hoc string.

## Detector class template

```python
"""<Name> detector — <one-line description of the anti-pattern>."""

from __future__ import annotations

from django_query_optimizer.detectors.base import BaseDetector
from django_query_optimizer.recommendations.base import ORMRecommendation, Severity
from django_query_optimizer.store import CapturedQuery


class <Name>Detector(BaseDetector):
    """Detects <anti-pattern> in captured queries."""

    def detect(self, queries: list[CapturedQuery]) -> list[ORMRecommendation]:
        """Analyse queries and return recommendations for <anti-pattern>."""
        recommendations: list[ORMRecommendation] = []
        # ... detection logic ...
        return recommendations
```

## Test template

```python
"""Unit tests for <Name>Detector."""

from __future__ import annotations

from django_query_optimizer.detectors.<name> import <Name>Detector
from django_query_optimizer.store import CapturedQuery


class Test<Name>Detector:
    def test_detects_<anti_pattern>(self) -> None:
        detector = <Name>Detector()
        queries = [CapturedQuery(sql="...", python_line=1)]

        recommendations = detector.detect(queries)

        assert len(recommendations) == 1
        assert recommendations[0].severity == Severity.<LEVEL>

    def test_no_false_positive_on_clean_queries(self) -> None:
        detector = <Name>Detector()

        recommendations = detector.detect([])

        assert recommendations == []
```

## After scaffolding, verify
- `detectors/__init__.py.__all__` includes the new class.
- `README.md` detector table has a new row.
- `CLAUDE.md` "Adding a New Detector" section's detector list (if present) is updated.
- `make docker-test` / `make lint-all` pass (mypy --strict, ruff).
