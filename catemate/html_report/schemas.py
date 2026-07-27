"""Pydantic schemas for visual HTML report specs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ChartType = Literal["trend", "bar", "share", "table", "kpi_row"]
BindingSource = Literal["chart_preset", "blueprint", "heuristic", "llm"]
ConfidenceLevel = Literal["high", "medium", "low"]
ChartRole = Literal["primary", "secondary"]
SectionStatus = Literal["solved", "partial", "unsolved"]
SpecStatus = Literal["draft", "confirmed"]


class ChartBinding(BaseModel):
    chart_id: str
    section_id: str
    table_id: str
    module_id: str = ""
    chart_type: ChartType
    title: str
    x_field: str | None = None
    y_fields: list[str] = Field(default_factory=list)
    series_field: str | None = None
    sort_rule: str | None = None
    top_n: int | None = None
    visible: bool = True
    role: ChartRole = "primary"
    binding_source: BindingSource = "heuristic"
    confidence: ConfidenceLevel = "medium"
    notes: list[str] = Field(default_factory=list)
    run_id: str = ""
    sheet_name: str = ""


class VisualReportSection(BaseModel):
    section_id: str
    title: str
    sub_question: str = ""
    narrative: str = ""
    status: SectionStatus = "solved"
    charts: list[ChartBinding] = Field(default_factory=list)


class VisualReportSpec(BaseModel):
    case_id: str = ""
    original_question: str = ""
    report_goal: str = ""
    executive_summary: str = ""
    sections: list[VisualReportSection] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    generated_at: str = ""
    spec_status: SpecStatus = "draft"
