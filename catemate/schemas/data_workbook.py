"""Schemas for V2 Data Workbook assembly."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BlueprintSheetRow(BaseModel):
    section_id: str
    title: str
    sub_question: str
    presentation: str = ""
    scope_note: str = ""


class PlanSheetRow(BaseModel):
    run_id: str
    section_id: str
    module_id: str
    metric_id: str
    grain: str
    is_sub_category: int = 0
    scope_kind: str = "standard"
    source_kind: str = "rawdata"
    table_id: str = ""
    status: str
    scope_label: str = ""
    missing: str = ""


class GapRow(BaseModel):
    gap_id: str
    section_id: str = ""
    reason: str
    suggestion: str = ""


class VerifyAuditRow(BaseModel):
    loop_iteration: int
    verdict: str
    exit_reason: str = ""
    solved_sections: str = ""
    unsolved_sections: str = ""


class DataWorkbookSpec(BaseModel):
    goal: str
    blueprint_rows: list[BlueprintSheetRow] = Field(default_factory=list)
    plan_rows: list[PlanSheetRow] = Field(default_factory=list)
    gap_rows: list[GapRow] = Field(default_factory=list)
    verify_rows: list[VerifyAuditRow] = Field(default_factory=list)
