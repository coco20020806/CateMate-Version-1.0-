"""Public entry for print_vertical_report generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from catemate.conclusion_brief.schemas import ConclusionBrief
from catemate.html_report.proposal_generator import load_visual_report_spec
from catemate.html_report.schemas import VisualReportSpec
from catemate.pipeline.manifest import utc_now_iso
from catemate.print_report.composer import compose_print_report_doc
from catemate.print_report.renderer import write_print_report_html
from catemate.print_report.schemas import PrintReportDoc


@dataclass
class PrintReportOutputs:
    case_id: str
    doc_path: Path
    html_path: Path


def _load_brief(path: Path | None) -> ConclusionBrief | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ConclusionBrief.model_validate(payload)


def generate_print_report(
    *,
    spec: VisualReportSpec | Path,
    workbook_path: Path,
    html_output: Path | None = None,
    doc_output: Path | None = None,
    conclusion_brief_path: Path | None = None,
    case_id: str = "",
    timestamp: str = "",
) -> PrintReportOutputs:
    loaded = load_visual_report_spec(spec) if isinstance(spec, Path) else spec
    if loaded.spec_status != "confirmed":
        raise ValueError("VisualReportSpec must be confirmed before generating print report.")

    brief = _load_brief(conclusion_brief_path)
    doc = compose_print_report_doc(spec=loaded, workbook_path=workbook_path, brief=brief)

    stamp = timestamp or utc_now_iso().replace(":", "").replace("-", "")[:15]
    cid = case_id or loaded.case_id or "case"
    base_dir = workbook_path.parent
    html_path = html_output or base_dir / f"print_report_{cid}_{stamp}.html"
    doc_path = doc_output or html_path.with_suffix(".json")

    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    write_print_report_html(doc, html_path)
    return PrintReportOutputs(case_id=cid, doc_path=doc_path, html_path=html_path)
