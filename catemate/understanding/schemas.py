"""Pydantic schemas for Requirement Understanding Layer v1."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class UnderstandingStatus(str, Enum):
    READY_FOR_MODULE_SELECTION = "ready_for_module_selection"
    NEEDS_MINIMUM_CONTEXT = "needs_minimum_context"
    OUT_OF_SCOPE = "out_of_scope"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    FREE_TEXT = "free_text"
    YES_NO = "yes_no"


class AnalysisIntent(str, Enum):
    MARKET_TREND = "market_trend"
    DAILY_PERFORMANCE = "daily_performance"
    PRICE_TIER = "price_tier"
    TOP_LISTING = "top_listing"
    TOP_SHOP = "top_shop"
    KEYWORDS = "keywords"
    CATEGORY_MAPPING = "category_mapping"
    SITE_COMPARISON = "site_comparison"
    PRICE_REFERENCE = "price_reference"
    UNKNOWN = "unknown"


class InferredCategoryCandidate(BaseModel):
    l1: str = ""
    l2: str = ""
    l3: str = ""
    category_path: str = ""
    reason: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class UnderstoodRequirement(BaseModel):
    business_background: str = ""
    delivery_audience: str = "待确认"
    delivery_format: str = "Excel"
    target_sites: list[str] = Field(default_factory=list)
    target_category_text: str = ""
    inferred_category: str = ""
    inferred_category_candidates: list[InferredCategoryCandidate] = Field(default_factory=list)
    category_level_hint: str = "unknown"
    analysis_intents: list[AnalysisIntent] = Field(default_factory=list)
    time_range: str = "使用源数据可覆盖范围，待确认"
    output_expectation: str = "数据需求 workbook / PPT-ready workbook"
    metric_definitions: dict[str, str] = Field(default_factory=dict)


class RequirementAssumption(BaseModel):
    assumption_id: str
    content: str
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_user_confirmation: bool = True


class RequirementUncertainty(BaseModel):
    uncertainty_id: str
    topic: str
    description: str
    blocks_module_selection: bool = False


class ClarifyingQuestion(BaseModel):
    question_id: str
    question: str
    reason: str = ""
    expected_answer_type: QuestionType = QuestionType.FREE_TEXT
    options: list[str] = Field(default_factory=list)
    blocks_module_selection: bool = False
    default_assumption: str = ""


class UserAnswer(BaseModel):
    question_id: str
    answer: str
    answered_at: str = ""


class RequirementReadiness(BaseModel):
    can_select_modules: bool = True
    blocking_reasons: list[str] = Field(default_factory=list)
    non_blocking_notes: list[str] = Field(default_factory=list)


class RequirementUnderstandingSpec(BaseModel):
    """Structured understanding output before module selection / planning."""

    spec_version: str = "requirement_understanding_v1"
    case_id: str = ""
    status: UnderstandingStatus
    original_request: str
    conversation_summary: str = ""
    understood: UnderstoodRequirement
    assumptions: list[RequirementAssumption] = Field(default_factory=list)
    uncertainties: list[RequirementUncertainty] = Field(default_factory=list)
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    user_answers: list[UserAnswer] = Field(default_factory=list)
    readiness: RequirementReadiness
