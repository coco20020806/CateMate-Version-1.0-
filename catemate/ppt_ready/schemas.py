"""Internal build schemas for generic PPT-ready workbook v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PptReadyBuildContext:
    case_id: str
    planning_spec_path: Path
    requirement_workbook_path: Path
    processed_manifest_path: Path
    processed_data_dir: Path


@dataclass
class PptReadySheetSpec:
    sheet_name: str
    chart_id: str
    chart_title: str
    chart_type: str
    data_module_id: str
    source_table_ids: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    output_status: str = "generated"  # generated / partial / unsupported / empty
    source_workbook_names: list[str] = field(default_factory=list)
    source_sheets: list[str] = field(default_factory=list)
    processed_csv_paths: list[str] = field(default_factory=list)
    source_rule_note: str = ""
    missing_data_note: str = ""
    null_reason_note: str = ""


@dataclass
class PptReadyWorkbookBuildResult:
    case_id: str
    output_path: Path
    sheets: list[PptReadySheetSpec] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # table_id -> lineage dict used while building (for data_notes)
    used_table_lineage: dict[str, dict[str, Any]] = field(default_factory=dict)
