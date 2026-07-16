"""Pydantic schemas for V2 solve loop orchestration."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

GrainType = Literal["category", "shop", "item"]
RunStatus = Literal["executable", "blocked_until_rawdata", "skipped", "executed", "failed"]
SolveVerdictType = Literal["solved", "partial", "retry"]
SolveLoopPhase = Literal[
    "blueprint",
    "compose",
    "catalog_check",
    "data_clarification",
    "execute",
    "metric_expansion",
    "verify",
    "done",
]
MetricRole = Literal["primary", "supplementary"]
ExitReason = Literal["solved", "user_declined_data", "max_iterations"] | None


class ExpectedShape(BaseModel):
    grain: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    presentation: str = "table"


class BlueprintSection(BaseModel):
    section_id: str
    title: str
    sub_question: str
    expected_shape: ExpectedShape = Field(default_factory=ExpectedShape)
    module_id: str = ""
    metric_id: str = ""
    grain: str = ""


class ReportBlueprint(BaseModel):
    goal: str
    sections: list[BlueprintSection] = Field(default_factory=list)
    loop_iteration: int = 1


class PlanRun(BaseModel):
    run_id: str
    section_id: str
    grain: GrainType = "category"
    module_id: str
    metric_id: str = "gmv"
    scope_label: str = ""
    required_catalog: str = ""
    table_id: str = ""
    status: RunStatus = "executable"
    missing: str = ""
    target_sites: list[str] = Field(default_factory=list)
    category_l1: str = ""
    category_l2: str = ""
    category_l3: str = ""
    related_concept_pack: dict[str, Any] | None = None
    related_min_score: float = 0.55


class AnalysisPlan(BaseModel):
    goal: str
    runs: list[PlanRun] = Field(default_factory=list)
    loop_iteration: int = 1


class UnsolvedSection(BaseModel):
    section_id: str
    reason: str = ""
    suggestion: str = ""


class SolveVerdict(BaseModel):
    verdict: SolveVerdictType = "retry"
    solved_sections: list[str] = Field(default_factory=list)
    unsolved_sections: list[UnsolvedSection] = Field(default_factory=list)
    loop_iteration: int = 1
    exit_reason: ExitReason = None
    notes: list[str] = Field(default_factory=list)


class RawdataClarificationQuestion(BaseModel):
    question_id: str
    question: str
    grain: str
    table_id: str
    catalog_key: str
    reason: str = ""
    answered: bool = False
    skipped: bool = False
    answer_path: str = ""


class MetricRecommendation(BaseModel):
    section_id: str
    metric_id: str
    role: MetricRole = "supplementary"
    reason: str = ""
    confidence: str = "medium"


class SectionMetricCoverage(BaseModel):
    section_id: str
    primary_metric: str = ""
    executed_metrics: list[str] = Field(default_factory=list)
    required_supplementary: list[str] = Field(default_factory=list)


class SolveLoopState(BaseModel):
    phase: SolveLoopPhase = "blueprint"
    loop_iteration: int = 1
    max_iterations: int = 3
    blueprint: ReportBlueprint | None = None
    plan: AnalysisPlan | None = None
    verdict: SolveVerdict | None = None
    rawdata_questions: list[RawdataClarificationQuestion] = Field(default_factory=list)
    user_declined_data: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuestionCategory(str, Enum):
    CLARIFY_BUSINESS = "clarify_business"
    RAWDATA = "rawdata"
