"""Build visual report spec and HTML from V2 Data Workbook + pipeline manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.core.paths import PROJECT_ROOT as CATEMATE_ROOT, ensure_project_dirs
from catemate.html_report.generator import propose_visual_report, render_html_report_from_spec
from catemate.html_report.proposal_generator import load_visual_report_spec, save_visual_report_spec
from catemate.pipeline.manifest import load_pipeline_manifest, resolve_manifest_path, update_and_save_manifest


def _default_spec_path(workbook_path: Path, case_id: str, timestamp: str) -> Path:
    return workbook_path.with_name(f"visual_report_spec_{case_id}_{timestamp}.json")


def _default_html_path(workbook_path: Path, case_id: str, timestamp: str) -> Path:
    return workbook_path.with_name(f"html_report_{case_id}_{timestamp}.html")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate VisualReportSpec and/or HTML report from V2 Data Workbook."
    )
    parser.add_argument("--pipeline-manifest", type=Path, required=True)
    parser.add_argument("--data-workbook", type=Path, default=None)
    parser.add_argument(
        "--mode",
        choices=["propose", "render", "all"],
        default="propose",
        help="propose=spec only; render=HTML from confirmed spec; all=propose+auto-confirm+render.",
    )
    parser.add_argument("--visual-report-spec", type=Path, default=None)
    parser.add_argument("--output-spec", type=Path, default=None)
    parser.add_argument("--output-html", type=Path, default=None)
    parser.add_argument("--max-tables", type=int, default=30)
    parser.add_argument("--max-rows", type=int, default=10)
    args = parser.parse_args()

    ensure_project_dirs()
    manifest_path = args.pipeline_manifest.resolve()
    manifest = load_pipeline_manifest(manifest_path)

    workbook_path = args.data_workbook
    if workbook_path is None:
        workbook_path = resolve_manifest_path(CATEMATE_ROOT, manifest.data_workbook_path)
    if workbook_path is None or not workbook_path.exists():
        print("error: data workbook not found", file=sys.stderr)
        return 1

    if not manifest.request_text.strip():
        print("error: manifest.request_text is empty", file=sys.stderr)
        return 1

    blueprint_path = resolve_manifest_path(CATEMATE_ROOT, manifest.report_blueprint_path)
    plan_path = resolve_manifest_path(CATEMATE_ROOT, manifest.analysis_plan_path)
    verdict_path = resolve_manifest_path(CATEMATE_ROOT, manifest.solve_verdict_path)
    conclusion_brief_path = resolve_manifest_path(CATEMATE_ROOT, manifest.conclusion_brief_json_path)

    spec_path = args.visual_report_spec or args.output_spec
    if spec_path is None:
        resolved = resolve_manifest_path(CATEMATE_ROOT, manifest.visual_report_spec_path)
        spec_path = resolved or _default_spec_path(workbook_path, manifest.case_id, manifest.timestamp)

    html_path: Path | None = args.output_html

    try:
        if args.mode in {"propose", "all"}:
            spec = propose_visual_report(
                workbook_path=workbook_path,
                original_question=manifest.request_text,
                case_id=manifest.case_id,
                timestamp=manifest.timestamp,
                blueprint_path=blueprint_path,
                plan_path=plan_path,
                verdict_path=verdict_path,
                conclusion_brief_path=conclusion_brief_path,
                spec_output=spec_path,
                max_tables=max(1, args.max_tables),
                max_rows_per_table=max(1, args.max_rows),
            )
            if args.mode == "all":
                confirmed = spec.model_copy(update={"spec_status": "confirmed"})
                save_visual_report_spec(confirmed, spec_path)

        if args.mode in {"render", "all"}:
            loaded = load_visual_report_spec(spec_path)
            if loaded.spec_status != "confirmed":
                print("error: visual report spec must be confirmed before render", file=sys.stderr)
                return 1
            html_path = render_html_report_from_spec(
                spec=spec_path,
                workbook_path=workbook_path,
                html_output=html_path or _default_html_path(workbook_path, manifest.case_id, manifest.timestamp),
                case_id=manifest.case_id,
                timestamp=manifest.timestamp,
            )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    update_and_save_manifest(
        manifest_path=manifest_path,
        case_id=manifest.case_id,
        timestamp=manifest.timestamp,
        request_text=manifest.request_text,
        provider=manifest.provider,
        model=manifest.model,
        planning_mode=manifest.planning_mode,
        case_config_path=resolve_manifest_path(CATEMATE_ROOT, manifest.case_config_path),
        understanding_spec_path=resolve_manifest_path(CATEMATE_ROOT, manifest.understanding_spec_path),
        report_blueprint_path=blueprint_path,
        analysis_plan_path=plan_path,
        solve_verdict_path=verdict_path,
        data_workbook_path=workbook_path,
        conclusion_brief_path=resolve_manifest_path(CATEMATE_ROOT, manifest.conclusion_brief_path),
        conclusion_brief_json_path=conclusion_brief_path,
        visual_report_spec_path=spec_path,
        html_report_path=html_path,
        status=manifest.status,
    )

    print(f"case_id: {manifest.case_id}")
    print(f"visual_report_spec: {spec_path}")
    if html_path is not None:
        print(f"html_report: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
