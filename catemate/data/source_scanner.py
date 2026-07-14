"""Scan raw data files and inspect expected workbook structure."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from catemate.schemas.category_requirement import FieldCheck, SheetCheck, SourceFile


def scan_excel_sources(raw_data_dir: Path) -> list[SourceFile]:
    """Return Excel files in the raw data directory."""
    files: list[SourceFile] = []
    for path in sorted(raw_data_dir.glob("*.xlsx")):
        stat = path.stat()
        files.append(
            SourceFile(
                path=path,
                size_bytes=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                matched_source_id="sph_monthly_category_performance"
                if "SPH" in path.name and "RM" in path.name
                else None,
            )
        )
    return files


def check_required_sheets(workbook_path: Path, required_sheets: list[str]) -> list[SheetCheck]:
    """Check whether expected sheets exist in a workbook."""
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    sheet_names = set(workbook.sheetnames)
    return [
        SheetCheck(sheet_name=name, exists=name in sheet_names, note="" if name in sheet_names else "源文件中未找到该 sheet")
        for name in required_sheets
    ]


def check_raw_data_fields(workbook_path: Path, required_fields: list[str], sheet_name: str = "Raw data") -> list[FieldCheck]:
    """Check required fields in the first row of Raw data."""
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    if sheet_name not in workbook.sheetnames:
        return [FieldCheck(field_name=field, exists=False, note=f"缺少 {sheet_name} sheet") for field in required_fields]

    sheet = workbook[sheet_name]
    first_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
    headers = {str(value).strip() for value in first_row if value is not None}
    return [
        FieldCheck(field_name=field, exists=field in headers, note="" if field in headers else "字段缺失")
        for field in required_fields
    ]
