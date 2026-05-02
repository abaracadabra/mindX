# Portions adapted from confident-ai/deepeval (Apache-2.0). See NOTICE.
"""
BaseMetric — abstract contract for mindX evaluation metrics.

Slim port of deepeval/metrics/base_metric.py:BaseMetric. Drops the
tracing decorator on __init_subclass__ (Confident-AI OTel hook) and
the synchronous measure() abstract — mindX is async-throughout, so
a_measure() is the only required method.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .test_case import LLMTestCase


class BaseMetric(ABC):
    """Abstract base for all evaluation metrics."""

    threshold: float = 0.5
    score: Optional[float] = None
    reason: Optional[str] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    evaluation_model: Optional[str] = None
    strict_mode: bool = False
    verbose_mode: bool = False

    @abstractmethod
    async def a_measure(self, test_case: LLMTestCase, **kwargs) -> float:
        """Score this test case asynchronously. Return a float in [0, 1]."""
        raise NotImplementedError

    def is_successful(self) -> bool:
        if self.error is not None:
            self.success = False
            return False
        try:
            self.success = self.score is not None and self.score >= self.threshold
        except TypeError:
            self.success = False
        return bool(self.success)
