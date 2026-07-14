"""Build a generic PPT-ready workbook from a confirmed requirement workbook."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.core.paths import OUTPUTS_DIR, PROCESSED_DATA_DIR, PROJECT_ROOT as CATEMATE_ROOT, ensure_project_dirs
from catemate.pipeline.manifest import load_pipeline_manifest, resolve_manifest_path, update_and_save_manifest
from catemate.ppt_ready.build_from_confirmed import ConfirmationGateBlockedError, build_ppt_ready_outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build generic PPT-ready workbook from confirmed requirement workbook + "
            "planning spec + processed data. Requires confirmation gate to pass."
        )
    )
    parser.add_argument(
        "--requirement-workbook",
        type=Path,
        default=None,
        help="Confirmed requirement workbook path.",
    )
    parser.add_argument(
        "--planning-spec",
        type=Path,
        default=None,
        help="Planning spec JSON path.",
    )
    parser.add_argument(
        "--pipeline-manifest",
        type=Path,
        default=None,
        help="Optional pipeline manifest; fills workbook/planning paths if not provided.",
    )
    parser.add_argument(
        "--processed-manifest",
        type=Path,
        default=PROCESSED_DATA_DIR / "processed_manifest.yaml",
        help="Path to processed_manifest.yaml",
    )
    parser.add_argument(
        "--processed-data-dir",
        type=Path,
        default=PROCESSED_DATA_DIR,
        help="Processed data directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path for PPT-ready workbook.",
    )
    parser.add_argument(
        "--no-html-preview",
        action="store_true",
        help="Skip HTML chart preview generation (default: generate preview).",
    )
    parser.add_argument(
        "--html-preview-output",
        type=Path,
        default=None,
        help="Optional HTML preview output path.",
    )
    parser.add_argument(
        "--html-preview-max-rows",
        type=int,
        default=1000,
        help="Max rows per chart considered for HTML preview (default: 1000).",
    )
    args = parser.parse_args()
    ensure_project_dirs()

    requirement_workbook = args.requirement_workbook
    planning_spec_path = args.planning_spec
    pipeline_manifest_path = args.pipeline_manifest
    pipeline = None

    if pipeline_manifest_path is not None:
        try:
            pipeline = load_pipeline_manifest(pipeline_manifest_path)
        except Exception as exc:
            print(f"Failed to load pipeline manifest: {exc}", file=sys.stderr)
            return 2
        if requirement_workbook is None:
            requirement_workbook = resolve_manifest_path(PROJECT_ROOT, pipeline.requirement_workbook_path)
        if planning_spec_path is None:
            planning_spec_path = resolve_manifest_path(PROJECT_ROOT, pipeline.planning_spec_path)

    if requirement_workbook is None or planning_spec_path is None:
        print(
            "Please provide --requirement-workbook and --planning-spec, "
            "or a --pipeline-manifest that contains both paths.",
            file=sys.stderr,
        )
        return 2

    try:
        outputs = build_ppt_ready_outputs(
            requirement_workbook=requirement_workbook,
            planning_spec_path=planning_spec_path,
            processed_manifest_path=args.processed_manifest,
            processed_data_dir=args.processed_data_dir,
            output_path=args.output,
            html_preview_output=args.html_preview_output,
            html_preview_max_rows=args.html_preview_max_rows,
            generate_html_preview=not args.no_html_preview,
        )
    except ConfirmationGateBlockedError as exc:
        print("Confirmation gate blocked PPT-ready generation.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        print(f"blocking_items: {len(exc.blocking_items)}", file=sys.stderr)
        for item in exc.blocking_items:
            print(
                f"- [{item.status}] {item.name} | suggested={item.suggested_value} | reason={item.reason}",
                file=sys.stderr,
            )
        return 1
    except Exception as exc:
        print(f"PPT-ready build failed: {exc}", file=sys.stderr)
        return 1

    if pipeline_manifest_path is not None and pipeline is not None:
        update_and_save_manifest(
            manifest_path=pipeline_manifest_path,
            case_id=pipeline.case_id,
            timestamp=pipeline.timestamp,
            request_text=pipeline.request_text,
            provider=pipeline.provider,
            model=pipeline.model,
            planning_mode=pipeline.planning_mode,
            case_config_path=resolve_manifest_path(PROJECT_ROOT, pipeline.case_config_path),
            understanding_spec_path=resolve_manifest_path(PROJECT_ROOT, pipeline.understanding_spec_path),
            module_selection_plan_path=resolve_manifest_path(PROJECT_ROOT, pipeline.module_selection_plan_path),
            planning_spec_path=resolve_manifest_path(PROJECT_ROOT, pipeline.planning_spec_path),
            requirement_workbook_path=resolve_manifest_path(PROJECT_ROOT, pipeline.requirement_workbook_path),
            ppt_ready_workbook_path=outputs.output_path,
            html_preview_path=outputs.html_preview_path,
            status="ppt_ready_generated",
        )

    print(f"case_id: {outputs.case_id}")
    print(f"output: {outputs.output_path}")
    if outputs.html_preview_path is not None:
        print(f"html_preview: {outputs.html_preview_path}")
    print(f"sheet_count: {outputs.sheet_count}")
    print(f"warning_count: {outputs.warning_count}")
    print("confirmation_gate: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
