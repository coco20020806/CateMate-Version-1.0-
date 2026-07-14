"""Module selection layer for CateMate."""

from catemate.module_selection.schemas import ModuleSelectionPlan
from catemate.module_selection.selector import ModuleSelectionSelector
from catemate.module_selection.validator import (
    summarize_module_selection_plan,
    validate_and_normalize_module_selection_plan,
)

__all__ = [
    "ModuleSelectionPlan",
    "ModuleSelectionSelector",
    "summarize_module_selection_plan",
    "validate_and_normalize_module_selection_plan",
]
