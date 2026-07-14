"""Generic PPT-ready workbook v1 builders."""

from catemate.ppt_ready.chart_data_builder import build_ppt_ready_sheets
from catemate.ppt_ready.html_preview import write_ppt_ready_html_preview
from catemate.ppt_ready.processed_data_reader import (
    get_table_entry,
    get_table_lineage,
    load_processed_manifest,
    load_processed_table,
    resolve_processed_csv_path,
)
from catemate.ppt_ready.schemas import (
    PptReadyBuildContext,
    PptReadySheetSpec,
    PptReadyWorkbookBuildResult,
)
from catemate.ppt_ready.workbook_writer import write_ppt_ready_workbook

__all__ = [
    "PptReadyBuildContext",
    "PptReadySheetSpec",
    "PptReadyWorkbookBuildResult",
    "build_ppt_ready_sheets",
    "get_table_entry",
    "get_table_lineage",
    "load_processed_manifest",
    "load_processed_table",
    "resolve_processed_csv_path",
    "write_ppt_ready_html_preview",
    "write_ppt_ready_workbook",
]
