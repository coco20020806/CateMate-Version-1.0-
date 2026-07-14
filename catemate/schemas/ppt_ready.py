"""Pydantic schemas for PPT-ready workbook specifications."""

from __future__ import annotations

from pydantic import BaseModel, Field

from catemate.schemas.enums import CategoryLevel, ChartType, DataSourceStatus


class PptReadyTableSpec(BaseModel):
    sheet_name: str
    chart_types: list[ChartType] = Field(default_factory=list)
    grain: str = ""
    category_level: CategoryLevel = CategoryLevel.UNKNOWN
    required_fields: list[str] = Field(default_factory=list)
    traceability_fields: list[str] = Field(default_factory=list)
    source_sheets: list[str] = Field(default_factory=list)
    status: DataSourceStatus = DataSourceStatus.AVAILABLE
    calculation_note: str = ""


class PptReadyWorkbookSpec(BaseModel):
    workbook_name: str = ""
    confirmed_mapping: str = ""
    target_site: str = ""
    target_category: str = ""
    tables: list[PptReadyTableSpec] = Field(default_factory=list)
    generate_preview_html: bool = False
    notes: list[str] = Field(default_factory=list)
