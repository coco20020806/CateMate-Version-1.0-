"""Build PPT-ready workbook + HTML preview from a confirmed requirement workbook."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from catemate.core.confirmation_gate import evaluate_confirmation_gate
from catemate.core.confirmation_reader import read_confirmation_items
from catemate.core.paths import PROJECT_ROOT
from catemate.planning.schemas import RequirementPlanningSpec
from catemate.ppt_ready.chart_data_builder import build_ppt_ready_sheets
from catemate.ppt_ready.html_preview import write_ppt_ready_html_preview
from catemate.ppt_ready.processed_data_reader import load_processed_manifest
from catemate.ppt_ready.schemas import PptReadyBuildContext, PptReadyWorkbookBuildResult
from catemate.ppt_ready.workbook_writer import write_ppt_ready_workbook
from catemate.schemas.confirmation import ConfirmationItem


class ConfirmationGateBlockedError(RuntimeError):
    """Raised when confirmation gate blocks PPT-ready generation."""

    def __init__(self, message: str, blocking_items: list[ConfirmationItem]):
        super().__init__(message)
        self.blocking_items = blocking_items


@dataclass
class PptReadyBuildOutputs:
    case_id: str
    output_path: Path
    html_preview_path: Path | None
    sheet_count: int
    warning_count: int
    gate_message: str


def build_ppt_ready_outputs(
    *,
    requirement_workbook: Path,
    planning_spec_path: Path,
    processed_manifest_path: Path,
    processed_data_dir: Path,
    output_path: Path | None = None,
    html_preview_output: Path | None = None,
    html_preview_max_rows: int = 1000,
    generate_html_preview: bool = True,
) -> PptReadyBuildOutputs:
    """Build PPT-ready workbook (and optional HTML preview). Requires confirmation gate pass."""
    requirement_workbook = requirement_workbook.resolve()
    planning_spec_path = planning_spec_path.resolve()

    if not requirement_workbook.exists():
        raise FileNotFoundError(f"Requirement workbook not found: {requirement_workbook}")
    if not planning_spec_path.exists():
        raise FileNotFoundError(f"Planning spec not found: {planning_spec_path}")
    if not processed_manifest_path.exists():
        raise FileNotFoundError(f"Processed manifest not found: {processed_manifest_path}")

    items = read_confirmation_items(requirement_workbook)
    gate = evaluate_confirmation_gate(items)
    if not gate.can_generate:
        raise ConfirmationGateBlockedError(gate.message, gate.blocking_items)

    payload = json.loads(planning_spec_path.read_text(encoding="utf-8"))
    planning_spec = RequirementPlanningSpec.model_validate(payload)
    processed_manifest = load_processed_manifest(processed_manifest_path)

    sheets, used_table_lineage = build_ppt_ready_sheets(
        planning_spec=planning_spec,
        manifest=processed_manifest,
        processed_data_dir=processed_data_dir,
        project_root=PROJECT_ROOT,
    )
    warnings: list[str] = []
    for sheet in sheets:
        if sheet.output_status not in {"partial", "unsupported", "empty"}:
            continue
        for note in sheet.notes:
            warnings.append(f"{sheet.chart_id}: {note}")
        if sheet.missing_data_note:
            warnings.append(f"{sheet.chart_id}: missing={sheet.missing_data_note}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    case_id = planning_spec.case_id or "unknown_case"
    resolved_output = output_path or (
        planning_spec_path.parent / f"ppt_ready_workbook_{case_id}_{timestamp}.xlsx"
    )

    context = PptReadyBuildContext(
        case_id=case_id,
        planning_spec_path=planning_spec_path,
        requirement_workbook_path=requirement_workbook,
        processed_manifest_path=processed_manifest_path.resolve(),
        processed_data_dir=processed_data_dir.resolve(),
    )
    result = PptReadyWorkbookBuildResult(
        case_id=case_id,
        output_path=resolved_output,
        sheets=sheets,
        warnings=warnings,
        used_table_lineage=used_table_lineage,
    )
    write_ppt_ready_workbook(
        result=result,
        context=context,
        output_path=resolved_output,
        planning_spec=planning_spec,
        gate_message=gate.message,
    )

    html_preview_path: Path | None = None
    if generate_html_preview:
        html_preview_path = html_preview_output or resolved_output.with_name(f"{resolved_output.stem}_preview.html")
        write_ppt_ready_html_preview(
            result=result,
            context=context,
            output_path=html_preview_path,
            max_rows=max(1, int(html_preview_max_rows)),
        )

    return PptReadyBuildOutputs(
        case_id=case_id,
        output_path=resolved_output,
        html_preview_path=html_preview_path,
        sheet_count=len(sheets),
        warning_count=len(warnings),
        gate_message=gate.message,
    )
