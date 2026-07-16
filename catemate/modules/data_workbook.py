"""Assemble V2 Data Workbook from SolveLoop outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from catemate.execution.result_collector import ExecutionResult
from catemate.orchestration.schemas import AnalysisPlan, ReportBlueprint, SolveLoopState, SolveVerdict
from catemate.schemas.data_workbook import (
    BlueprintSheetRow,
    DataWorkbookSpec,
    GapRow,
    PlanSheetRow,
    VerifyAuditRow,
)


def build_data_workbook_spec(
    *,
    blueprint: ReportBlueprint,
    plan: AnalysisPlan,
    verdict: SolveVerdict,
    execution: ExecutionResult | None = None,
) -> DataWorkbookSpec:
    blueprint_rows = [
        BlueprintSheetRow(
            section_id=s.section_id,
            title=s.title,
            sub_question=s.sub_question,
            presentation=s.expected_shape.presentation,
        )
        for s in blueprint.sections
    ]
    plan_rows = [
        PlanSheetRow(
            run_id=r.run_id,
            section_id=r.section_id,
            module_id=r.module_id,
            metric_id=r.metric_id,
            grain=r.grain,
            status=r.status,
            scope_label=r.scope_label,
            missing=r.missing,
        )
        for r in plan.runs
    ]
    gap_rows = [
        GapRow(
            gap_id=f"gap_{u.section_id}",
            section_id=u.section_id,
            reason=u.reason,
            suggestion=u.suggestion,
        )
        for u in verdict.unsolved_sections
    ]
    verify_rows = [
        VerifyAuditRow(
            loop_iteration=verdict.loop_iteration,
            verdict=verdict.verdict,
            exit_reason=verdict.exit_reason or "",
            solved_sections=",".join(verdict.solved_sections),
            unsolved_sections=",".join(u.section_id for u in verdict.unsolved_sections),
        )
    ]
    _ = execution
    return DataWorkbookSpec(
        goal=blueprint.goal,
        blueprint_rows=blueprint_rows,
        plan_rows=plan_rows,
        gap_rows=gap_rows,
        verify_rows=verify_rows,
    )


def write_data_workbook(
    *,
    state: SolveLoopState,
    execution: ExecutionResult,
    output_path: Path,
) -> Path:
    if state.blueprint is None or state.plan is None or state.verdict is None:
        raise ValueError("SolveLoopState must include blueprint, plan, and verdict")

    spec = build_data_workbook_spec(
        blueprint=state.blueprint,
        plan=state.plan,
        verdict=state.verdict,
        execution=execution,
    )
    wb = Workbook()
    wb.remove(wb.active)

    _write_sheet(wb, "Blueprint", ["section_id", "title", "sub_question", "presentation"], spec.blueprint_rows)
    _write_sheet(
        wb,
        "Plan",
        ["run_id", "section_id", "module_id", "metric_id", "grain", "status", "scope_label", "missing"],
        spec.plan_rows,
    )
    _write_sheet(wb, "Gaps", ["gap_id", "section_id", "reason", "suggestion"], spec.gap_rows)
    _write_sheet(
        wb,
        "Verify",
        ["loop_iteration", "verdict", "exit_reason", "solved_sections", "unsolved_sections"],
        spec.verify_rows,
    )

    for table_id, df in execution.dataframes.items():
        sheet_name = _safe_sheet_name(f"Data.{table_id}")
        ws = wb.create_sheet(title=sheet_name)
        _write_dataframe(ws, df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


def _write_sheet(wb: Workbook, title: str, headers: list[str], rows: list) -> None:
    ws = wb.create_sheet(title=title)
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append([getattr(row, h) for h in headers])
    for idx, _ in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = 18


def _write_dataframe(ws, df: pd.DataFrame) -> None:
    note = _monthly_aggregation_note(df)
    if note:
        ws.append([note])
    header_row = ws.max_row + 1
    ws.append(list(df.columns))
    for cell in ws[header_row]:
        cell.font = Font(bold=True)
    for record in df.itertuples(index=False, name=None):
        ws.append(list(record))


def _safe_sheet_name(name: str) -> str:
    invalid = set(r'[]:*?/\\')
    cleaned = "".join("_" if ch in invalid else ch for ch in name)
    return cleaned[:31] or "Data"


def _monthly_aggregation_note(df: pd.DataFrame) -> str:
    columns = {str(col).strip().lower() for col in df.columns}
    if "grass_month" in columns or "month" in columns:
        return "注：本表为月度聚合数据（grass_month/month）。"
    return ""
