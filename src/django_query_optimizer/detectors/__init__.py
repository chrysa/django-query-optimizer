"""Detectors package — ORM anti-pattern detectors."""

from django_query_optimizer.detectors.base import BaseDetector
from django_query_optimizer.detectors.n_plus_one import NplusOneDetector
from django_query_optimizer.detectors.select_related import SelectRelatedDetector

__all__ = ["BaseDetector", "NplusOneDetector", "SelectRelatedDetector"]
