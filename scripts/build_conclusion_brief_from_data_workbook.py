"""Build conclusion brief from V2 Data Workbook + pipeline manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.conclusion_brief.generator import build_conclusion_brief_outputs
from catemate.core.paths import PROJECT_ROOT as CATEMATE_ROOT, ensure_project_dirs
from catemate.pipeline.manifest import load_pipeline_manifest, resolve_manifest_path, update_and_save_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate LLM conclusion brief from V2 Data Workbook and pipeline manifest."
    )
    parser.add_argument(
        "--pipeline-manifest",
        type=Path,
        required=True,
        help="Pipeline manifest JSON path.",
    )
    parser.add_argument(
        "--data-workbook",
        type=Path,
        default=None,
        help="Optional override for data workbook path.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional output JSON path.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help="Optional output Markdown path.",
    )
    parser.add_argument(
        "--max-tables",
        type=int,
        default=30,
        help="Max Data.* tables in digest.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=10,
        help="Max rows per table in digest.",
    )
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

    try:
        outputs = build_conclusion_brief_outputs(
            workbook_path=workbook_path,
            original_question=manifest.request_text,
            blueprint_path=blueprint_path,
            plan_path=plan_path,
            verdict_path=verdict_path,
            json_output=args.output_json,
            md_output=args.output_md,
            case_id=manifest.case_id,
            timestamp=manifest.timestamp,
            max_tables=max(1, args.max_tables),
            max_rows_per_table=max(1, args.max_rows),
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
        conclusion_brief_path=outputs.md_path,
        conclusion_brief_json_path=outputs.json_path,
        status=manifest.status,
    )

    print(f"case_id: {outputs.case_id}")
    print(f"conclusion_brief_json: {outputs.json_path}")
    print(f"conclusion_brief_md: {outputs.md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
