"""daily_cncb_performance data module package."""

from catemate.scope.schemas import ScopedFrame

from .compute import ComputeParams, compute

__all__ = ["ComputeParams", "ScopedFrame", "compute"]
