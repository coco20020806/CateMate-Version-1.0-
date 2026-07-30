"""Build print_vertical_report HTML from confirmed Visual Report Spec."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.core.paths import PROJECT_ROOT as CATEMATE_ROOT, ensure_project_dirs
from catemate.html_report.proposal_generator import load_visual_report_spec
from catemate.pipeline.manifest import load_pipeline_manifest, resolve_manifest_path, update_and_save_manifest
from catemate.print_report.generator import generate_print_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate fuzzy print_vertical_report HTML from confirmed VisualReportSpec."
    )
    parser.add_argument("--pipeline-manifest", type=Path, default=None)
    parser.add_argument("--visual-spec", type=Path, default=None)
    parser.add_argument("--data-workbook", type=Path, default=None)
    parser.add_argument("--conclusion-brief-json", type=Path, default=None)
    parser.add_argument("--output-html", type=Path, default=None)
    parser.add_argument("--output-doc", type=Path, default=None)
    args = parser.parse_args()

    ensure_project_dirs()

    manifest = None
    manifest_path = args.pipeline_manifest.resolve() if args.pipeline_manifest else None
    if manifest_path is not None:
        manifest = load_pipeline_manifest(manifest_path)

    workbook_path = args.data_workbook
    spec_path = args.visual_spec
    brief_path = args.conclusion_brief_json
    case_id = ""
    timestamp = ""

    if manifest is not None:
        case_id = manifest.case_id
        timestamp = manifest.timestamp
        if workbook_path is None:
            workbook_path = resolve_manifest_path(CATEMATE_ROOT, manifest.data_workbook_path)
        if spec_path is None:
            spec_path = resolve_manifest_path(CATEMATE_ROOT, manifest.visual_report_spec_path)
        if brief_path is None:
            brief_path = resolve_manifest_path(CATEMATE_ROOT, manifest.conclusion_brief_json_path)

    if workbook_path is None or not Path(workbook_path).exists():
        print("error: data workbook not found", file=sys.stderr)
        return 1
    if spec_path is None or not Path(spec_path).exists():
        print("error: visual report spec not found", file=sys.stderr)
        return 1

    workbook_path = Path(workbook_path).resolve()
    spec_path = Path(spec_path).resolve()
    brief_path = Path(brief_path).resolve() if brief_path else None

    try:
        loaded = load_visual_report_spec(spec_path)
        if loaded.spec_status != "confirmed":
            print("error: visual report spec must be confirmed before print report", file=sys.stderr)
            return 1
        outputs = generate_print_report(
            spec=loaded,
            workbook_path=workbook_path,
            html_output=args.output_html,
            doc_output=args.output_doc,
            conclusion_brief_path=brief_path,
            case_id=case_id or loaded.case_id,
            timestamp=timestamp,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if manifest_path is not None and manifest is not None:
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
            report_blueprint_path=resolve_manifest_path(CATEMATE_ROOT, manifest.report_blueprint_path),
            analysis_plan_path=resolve_manifest_path(CATEMATE_ROOT, manifest.analysis_plan_path),
            solve_verdict_path=resolve_manifest_path(CATEMATE_ROOT, manifest.solve_verdict_path),
            data_workbook_path=workbook_path,
            conclusion_brief_path=resolve_manifest_path(CATEMATE_ROOT, manifest.conclusion_brief_path),
            conclusion_brief_json_path=brief_path,
            visual_report_spec_path=spec_path,
            html_report_path=resolve_manifest_path(CATEMATE_ROOT, manifest.html_report_path),
            print_report_path=outputs.html_path,
            status=manifest.status,
        )

    print(f"case_id: {outputs.case_id}")
    print(f"print_report_doc: {outputs.doc_path}")
    print(f"print_report: {outputs.html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
