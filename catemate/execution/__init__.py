"""Execution package."""

from .result_collector import ExecutionResult
from .runner import execute_analysis_plan

__all__ = ["ExecutionResult", "execute_analysis_plan"]
