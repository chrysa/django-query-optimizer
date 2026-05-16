"""Base detector protocol for ORM anti-pattern detectors."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from django_query_optimizer.collectors.query_collector import CapturedQuery
from django_query_optimizer.recommendations.base import ORMRecommendation


@runtime_checkable
class BaseDetector(Protocol):
    """Protocol that all ORM detectors must satisfy.

    A detector receives a list of :class:`CapturedQuery` objects and returns
    a (possibly empty) list of :class:`ORMRecommendation` instances.

    Example::

        class MyDetector:
            def detect(self, queries: list[CapturedQuery]) -> list[ORMRecommendation]:
                return []

        assert isinstance(MyDetector(), BaseDetector)
    """

    def detect(self, queries: list[CapturedQuery]) -> list[ORMRecommendation]:
        """Analyse queries and return a list of recommendations."""
        ...
