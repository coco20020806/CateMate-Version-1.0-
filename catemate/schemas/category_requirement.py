"""Pydantic schemas for category analysis requirements."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from catemate.schemas.confirmation import ConfirmationItem
from catemate.schemas.enums import CategoryLevel, ChartType, ConfirmationStatus, DataSourceStatus


class SourceFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path
    size_bytes: int
    modified_time: str
    matched_source_id: str | None = None


class SheetCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    sheet_name: str
    exists: bool
    note: str = ""


class FieldCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    field_name: str
    exists: bool
    note: str = ""


class CategoryMappingCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_text: str
    candidate_path: str
    candidate_l1: str = ""
    candidate_l2: str = ""
    candidate_l3: str = ""
    category_level: CategoryLevel = CategoryLevel.UNKNOWN
    confidence: str = "unknown"
    confirmation_required: bool = True
    reason: str = ""


class RequirementBrief(BaseModel):
    """Structured version of a user's category analysis request."""

    original_request: str
    business_background: str = ""
    analysis_purpose: str = ""
    delivery_audience: str = ""
    delivery_format: str = "Excel"
    target_category_text: str = ""
    target_sites: list[str] = Field(default_factory=list)
    time_range: str = ""
    requested_outputs: list[str] = Field(default_factory=list)
    special_rules: list[str] = Field(default_factory=list)


class RequirementContext(BaseModel):
    """Runtime context used by the current MVP generator."""

    original_request: str
    target_category_text: str
    business_background: str = ""
    delivery_audience: str = "\u5f85\u786e\u8ba4"
    delivery_format: str = "Excel"
    target_sites: list[str] = Field(default_factory=list)
    time_range: str = "\u4f7f\u7528\u6e90\u6570\u636e\u53ef\u8986\u76d6\u8303\u56f4\uff0c\u5f85\u786e\u8ba4"


class DataSourceSpec(BaseModel):
    source_id: str
    name: str = ""
    file_pattern: str = ""
    required_sheets: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)
    status: DataSourceStatus = DataSourceStatus.PARTIAL
    note: str = ""


class DataAvailabilityCheck(BaseModel):
    source_id: str
    status: DataSourceStatus
    sheet_checks: list[SheetCheck] = Field(default_factory=list)
    field_checks: list[FieldCheck] = Field(default_factory=list)
    missing_impact: str = ""
    next_action: str = ""


class RequirementSummaryRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    content: str


class CategoryCandidateRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_text: str = ""
    candidate_path: str = ""
    l1: str = ""
    l2: str = ""
    l3: str = ""
    match_type: str = ""
    confirmation_status: str = "\u5f85\u786e\u8ba4"
    note: str = ""


class AnalysisPlanRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    analysis_block: str
    question: str
    support_status: str
    dependencies: str
    note: str = ""
    module_id: str = ""
    planning_reason: str = ""


class DataRequirementRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_source: str
    field_or_sheet: str
    is_required: str
    purpose: str
    missing_impact: str
    current_note: str = ""
    module_id: str = ""
    table_id: str = ""
    planning_reason: str = ""
    source_notes: str = ""


class SourceCheckRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    check_type: str
    object_name: str
    status: str
    note: str = ""


class PreprocessPlanRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    step: str
    input_name: str
    output_name: str
    note: str = ""


class ChartDataRequirementRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    chart_page: str
    required_table: str
    fields: str
    status: str
    note: str = ""
    chart_type: ChartType | None = None
    data_module_id: str = ""
    table_ids: str = ""
    grain: str = ""
    metrics: str = ""
    dimensions: str = ""
    planning_reason: str = ""
    chart_intent: str = ""
    x_axis: str = ""
    y_axis: str = ""
    series: str = ""
    sort_rule: str = ""
    optional_flag: str = ""
    selection_reason: str = ""


class ConfirmationTemplateItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    question: str = ""
    suggested_value: str = ""
    status: ConfirmationStatus = ConfirmationStatus.PENDING_CONFIRMATION
    reason: str = ""


class CategoryAnalysisCaseConfig(BaseModel):
    """Case-level configuration used to build requirement workbooks."""

    model_config = ConfigDict(populate_by_name=True)

    case_id: str
    project_name: str
    original_request: str
    target_category_text: str
    business_background: str = ""
    delivery_audience: str = "待确认"
    delivery_format: str = "Excel"
    target_sites: list[str] = Field(default_factory=list)
    time_range: str = "使用源数据可覆盖范围，待确认"
    source_file_keywords: list[str] = Field(default_factory=list)
    required_sheets: list[str] = Field(default_factory=list)
    raw_fields_sheet_name: str = "Raw data"
    required_fields: list[str] = Field(default_factory=list)
    category_tree_source_keywords: list[str] = Field(default_factory=list)
    category_tree_sheet_name: str = "SPH类目树"
    category_keywords: list[str] = Field(default_factory=list)
    analysis_plan: list[AnalysisPlanRow] = Field(default_factory=list)
    data_requirements: list[DataRequirementRow] = Field(default_factory=list)
    preprocess_plan: list[PreprocessPlanRow] = Field(default_factory=list)
    chart_requirements: list[ChartDataRequirementRow] = Field(default_factory=list)
    confirmation_templates: list[ConfirmationTemplateItem] = Field(
        default_factory=list,
        alias="static_confirmation_items",
    )


class CategoryAnalysisRequirementSpec(BaseModel):
    """Structured specification for a category analysis data requirement workbook."""

    project_name: str = "HKCB Collectible Category Insight \u6837\u4f8b"
    requirement_summary: list[RequirementSummaryRow] = Field(default_factory=list)
    category_candidates: list[CategoryCandidateRow] = Field(default_factory=list)
    analysis_plan: list[AnalysisPlanRow] = Field(default_factory=list)
    data_requirements: list[DataRequirementRow] = Field(default_factory=list)
    source_checks: list[SourceCheckRow] = Field(default_factory=list)
    preprocess_plan: list[PreprocessPlanRow] = Field(default_factory=list)
    chart_requirements: list[ChartDataRequirementRow] = Field(default_factory=list)
    confirmation_items: list[ConfirmationItem] = Field(default_factory=list)
    allowed_final_statuses: list[ConfirmationStatus] = Field(
        default_factory=lambda: [ConfirmationStatus.CONFIRMED, ConfirmationStatus.NOT_NEEDED]
    )
    blocking_statuses: list[ConfirmationStatus] = Field(
        default_factory=lambda: [
            ConfirmationStatus.PENDING_CONFIRMATION,
            ConfirmationStatus.PENDING_SUPPLEMENT,
            ConfirmationStatus.SUPPLEMENTED,
            ConfirmationStatus.BLOCKED,
        ]
    )
