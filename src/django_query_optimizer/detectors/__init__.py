"""Detectors package — ORM anti-pattern detectors."""

from django_query_optimizer.detectors.base import BaseDetector
from django_query_optimizer.detectors.n_plus_one import NplusOneDetector

__all__ = ["BaseDetector", "NplusOneDetector"]
