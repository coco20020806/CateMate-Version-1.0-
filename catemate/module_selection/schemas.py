"""Pydantic schemas for Module Selection Layer v1."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModuleDecision(str, Enum):
    SELECTED = "selected"
    OPTIONAL = "optional"
    REJECTED = "rejected"
    NEEDS_CONFIRMATION = "needs_confirmation"


class SelectionConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ChartRuleSource(str, Enum):
    MODULE_DEFAULT = "module_default"
    USER_REQUEST = "user_request"
    SYSTEM_INFERRED = "system_inferred"


class SelectedChartIntent(BaseModel):
    chart_intent: str
    chart_title: str = ""
    chart_type: str
    source_default_chart: str = ""
    x_axis: str | None = None
    y_axis: list[str] = Field(default_factory=list)
    series: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    sort_rule: str = ""
    top_n: int | None = None
    rule_source: ChartRuleSource = ChartRuleSource.MODULE_DEFAULT
    override_reason: str = ""


class ModuleSelectionItem(BaseModel):
    module_id: str
    module_name: str = ""
    decision: ModuleDecision
    confidence: SelectionConfidence = SelectionConfidence.MEDIUM
    matched_intents: list[str] = Field(default_factory=list)
    matched_user_need: str = ""
    reason: str
    source_tables: list[str] = Field(default_factory=list)
    selected_chart_intents: list[SelectedChartIntent] = Field(default_factory=list)
    inherited_chart_rules: dict[str, Any] = Field(default_factory=dict)
    inherited_limitations: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confirmation_questions: list[str] = Field(default_factory=list)


class ModuleSelectionPlan(BaseModel):
    """Structured module selection output before RequirementPlanningSpec."""

    spec_version: str = "module_selection_v1"
    case_id: str = ""
    understanding_spec_path: str = ""
    status: str = "ready"
    original_request: str = ""
    understanding_summary: str = ""
    selected_modules: list[ModuleSelectionItem] = Field(default_factory=list)
    optional_modules: list[ModuleSelectionItem] = Field(default_factory=list)
    rejected_modules: list[ModuleSelectionItem] = Field(default_factory=list)
    needs_confirmation_modules: list[ModuleSelectionItem] = Field(default_factory=list)
    global_assumptions: list[str] = Field(default_factory=list)
    global_warnings: list[str] = Field(default_factory=list)

    def all_items(self) -> list[ModuleSelectionItem]:
        return (
            list(self.selected_modules)
            + list(self.optional_modules)
            + list(self.rejected_modules)
            + list(self.needs_confirmation_modules)
        )
