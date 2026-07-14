"""Pydantic schemas for CateMate AI planning specs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


FitLevel = Literal["high", "medium", "low"]
ChartTypeName = Literal["bubble", "bar", "trend", "share", "table", "unknown"]
CategoryLevelName = Literal["L1", "L2", "L3", "unknown"]


class PlanningTargetCategory(BaseModel):
    level: CategoryLevelName = "unknown"
    path: str
    confidence: float = 0.0
    reason: str = ""


class PlanningDataModuleMatch(BaseModel):
    module_id: str
    module_name: str = ""
    fit_level: FitLevel
    reason: str
    required_tables: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class PlanningChartProposal(BaseModel):
    chart_id: str
    title: str
    chart_type: ChartTypeName = "unknown"
    data_module_id: str
    table_ids: list[str] = Field(default_factory=list)
    grain: str = ""
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    reason: str = ""
    chart_intent: str = ""
    x_axis: str | None = None
    y_axis: list[str] = Field(default_factory=list)
    series: str | None = None
    sort_rule: str = ""
    top_n: int | None = None
    rule_source: str = ""
    module_decision: str = ""
    selection_reason: str = ""
    optional: bool = False


class PlanningMissingDataQuestion(BaseModel):
    question_id: str
    question: str
    reason: str
    blocks_ppt_ready: bool = True


class RequirementPlanningSpec(BaseModel):
    """Structured planning output used before building requirement workbooks."""

    case_id: str
    project_name: str
    interpreted_request: str
    target_categories: list[PlanningTargetCategory] = Field(default_factory=list)
    matched_data_modules: list[PlanningDataModuleMatch] = Field(default_factory=list)
    proposed_charts: list[PlanningChartProposal] = Field(default_factory=list)
    missing_data_questions: list[PlanningMissingDataQuestion] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    source_notes: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
