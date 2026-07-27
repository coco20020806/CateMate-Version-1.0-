"""Public entry points for HTML visual report generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from catemate.html_report.proposal_generator import (
    load_visual_report_spec,
    propose_visual_report_spec,
    save_visual_report_spec,
)
from catemate.html_report.renderer import render_html_report
from catemate.html_report.schemas import VisualReportSpec
from catemate.pipeline.manifest import utc_now_iso


@dataclass
class HtmlReportOutputs:
    case_id: str
    spec_path: Path
    html_path: Path | None = None


def _default_spec_path(*, workbook_path: Path, case_id: str, timestamp: str) -> Path:
    stem = f"visual_report_spec_{case_id}_{timestamp}" if case_id and timestamp else f"visual_report_spec_{workbook_path.stem}"
    return workbook_path.with_name(f"{stem}.json")


def _default_html_path(*, workbook_path: Path, case_id: str, timestamp: str) -> Path:
    stem = f"html_report_{case_id}_{timestamp}" if case_id and timestamp else f"html_report_{workbook_path.stem}"
    return workbook_path.with_name(f"{stem}.html")


def propose_visual_report(
    *,
    workbook_path: Path,
    original_question: str,
    case_id: str = "",
    timestamp: str = "",
    blueprint_path: Path | None = None,
    plan_path: Path | None = None,
    verdict_path: Path | None = None,
    conclusion_brief_path: Path | None = None,
    spec_output: Path | None = None,
    max_tables: int = 30,
    max_rows_per_table: int = 10,
    ai_client=None,
) -> VisualReportSpec:
    spec = propose_visual_report_spec(
        workbook_path=workbook_path,
        original_question=original_question,
        case_id=case_id,
        blueprint_path=blueprint_path,
        plan_path=plan_path,
        verdict_path=verdict_path,
        conclusion_brief_path=conclusion_brief_path,
        max_tables=max_tables,
        max_rows_per_table=max_rows_per_table,
        ai_client=ai_client,
    )
    if not spec.generated_at:
        spec = spec.model_copy(update={"generated_at": utc_now_iso()})

    out = spec_output or _default_spec_path(
        workbook_path=workbook_path,
        case_id=case_id,
        timestamp=timestamp,
    )
    save_visual_report_spec(spec, out)
    return spec


def render_html_report_from_spec(
    *,
    spec: VisualReportSpec | Path,
    workbook_path: Path,
    html_output: Path | None = None,
    case_id: str = "",
    timestamp: str = "",
) -> Path:
    if isinstance(spec, Path):
        spec = load_visual_report_spec(spec)
    if spec.spec_status != "confirmed":
        raise ValueError("Cannot render HTML until VisualReportSpec is confirmed.")

    out = html_output or _default_html_path(
        workbook_path=workbook_path,
        case_id=case_id,
        timestamp=timestamp,
    )
    return render_html_report(spec=spec, workbook_path=workbook_path, output_path=out)


def build_html_report_outputs(
    *,
    workbook_path: Path,
    original_question: str,
    case_id: str = "",
    timestamp: str = "",
    blueprint_path: Path | None = None,
    plan_path: Path | None = None,
    verdict_path: Path | None = None,
    conclusion_brief_path: Path | None = None,
    spec_output: Path | None = None,
    html_output: Path | None = None,
    mode: str = "propose",
    spec_path: Path | None = None,
    ai_client=None,
) -> HtmlReportOutputs:
    spec_out = spec_output or _default_spec_path(
        workbook_path=workbook_path,
        case_id=case_id,
        timestamp=timestamp,
    )
    html_out: Path | None = None

    if mode in {"propose", "all"}:
        propose_visual_report(
            workbook_path=workbook_path,
            original_question=original_question,
            case_id=case_id,
            timestamp=timestamp,
            blueprint_path=blueprint_path,
            plan_path=plan_path,
            verdict_path=verdict_path,
            conclusion_brief_path=conclusion_brief_path,
            spec_output=spec_out,
            ai_client=ai_client,
        )

    if mode in {"render", "all"}:
        loaded_spec_path = spec_path or spec_out
        spec = load_visual_report_spec(loaded_spec_path)
        if mode == "all" and spec.spec_status != "confirmed":
            spec = spec.model_copy(update={"spec_status": "confirmed"})
            save_visual_report_spec(spec, loaded_spec_path)
        html_out = render_html_report_from_spec(
            spec=loaded_spec_path,
            workbook_path=workbook_path,
            html_output=html_output,
            case_id=case_id,
            timestamp=timestamp,
        )

    return HtmlReportOutputs(case_id=case_id, spec_path=spec_out, html_path=html_out)
