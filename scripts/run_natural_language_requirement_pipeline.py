"""One-click pipeline with switchable planning modes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.core.paths import CONFIG_DIR, OUTPUTS_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR, ensure_project_dirs
from catemate.pipeline.runner import (
    PipelineRunResult,
    run_pipeline_continue_after_category_confirmation,
    run_pipeline_continue_from_manifest,
    run_pipeline_from_request_text,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run natural-language requirement pipeline.")
    parser.add_argument("--request-text", type=str, default="", help="Raw user request text.")
    parser.add_argument(
        "--request-file",
        type=Path,
        default=None,
        help="Path to txt/md file containing request text. If set, it overrides --request-text.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUTS_DIR,
        help="Directory for pipeline artifacts. Defaults to outputs.",
    )
    parser.add_argument(
        "--reference-cases-dir",
        type=Path,
        default=CONFIG_DIR / "cases",
        help="Directory of reference case YAML files.",
    )
    parser.add_argument(
        "--data-modules-dir",
        type=Path,
        default=CONFIG_DIR / "data_modules",
        help="Directory of data module YAML files.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROCESSED_DATA_DIR / "processed_manifest.yaml",
        help="Path to processed_manifest.yaml",
    )
    parser.add_argument(
        "--raw-data-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Path to raw data directory.",
    )
    parser.add_argument(
        "--processed-data-dir",
        type=Path,
        default=PROCESSED_DATA_DIR,
        help="Path to processed data directory.",
    )
    parser.add_argument(
        "--category-tree-lookup",
        type=Path,
        default=RAW_DATA_DIR / "category_tree_en.json",
        help="Path to category tree lookup CSV for understanding L3 matching.",
    )
    parser.add_argument(
        "--stop-after-case-config",
        action="store_true",
        help="Stop after generating and saving case config YAML.",
    )
    parser.add_argument(
        "--stop-after-planning",
        action="store_true",
        help="Stop after generating and saving planning spec JSON.",
    )
    parser.add_argument(
        "--planning-mode",
        choices=["ai_direct", "module_selection", "v2_solve_loop"],
        default="ai_direct",
        help="Planning mode: ai_direct, module_selection, or v2_solve_loop.",
    )
    parser.add_argument(
        "--stop-after-understanding",
        action="store_true",
        help="Stop after generating RequirementUnderstandingSpec (module_selection mode only).",
    )
    parser.add_argument(
        "--stop-after-module-selection",
        action="store_true",
        help="Stop after generating ModuleSelectionPlan (module_selection mode only).",
    )
    parser.add_argument(
        "--continue-from-manifest",
        type=Path,
        default=None,
        help="Resume pipeline from an existing pipeline manifest JSON (module_selection mode).",
    )
    parser.add_argument(
        "--continue-after-category-confirmation",
        type=Path,
        default=None,
        help="Resume pipeline after user confirmed categories on manifest.",
    )
    args = parser.parse_args()

    stop_flags = [
        args.stop_after_case_config,
        args.stop_after_understanding,
        args.stop_after_module_selection,
        args.stop_after_planning,
    ]
    if sum(1 for item in stop_flags if item) > 1:
        print("Please use only one stop flag at a time.", file=sys.stderr)
        return 2

    stop_after = None
    if args.stop_after_case_config:
        stop_after = "case_config"
    elif args.stop_after_understanding:
        stop_after = "understanding"
    elif args.stop_after_module_selection:
        stop_after = "module_selection"
    elif args.stop_after_planning:
        stop_after = "planning"

    if args.continue_after_category_confirmation is not None:
        ensure_project_dirs()
        result = run_pipeline_continue_after_category_confirmation(
            args.continue_after_category_confirmation,
            data_modules_dir=args.data_modules_dir,
            raw_data_dir=args.raw_data_dir,
            processed_data_dir=args.processed_data_dir,
            stop_after=stop_after,
        )
        _print_cli_summary(result)
        return result.exit_code

    if args.continue_from_manifest is not None:
        ensure_project_dirs()
        result = run_pipeline_continue_from_manifest(
            args.continue_from_manifest,
            data_modules_dir=args.data_modules_dir,
            raw_data_dir=args.raw_data_dir,
            processed_data_dir=args.processed_data_dir,
            stop_after=stop_after,
        )
        _print_cli_summary(result)
        return result.exit_code

    if args.planning_mode == "ai_direct" and (
        args.stop_after_understanding or args.stop_after_module_selection
    ):
        print(
            "planning-mode=ai_direct does not produce understanding/module-selection artifacts; "
            "please use --stop-after-case-config or --stop-after-planning.",
            file=sys.stderr,
        )
        return 2

    ensure_project_dirs()

    result = run_pipeline_from_request_text(
        request_text=args.request_text,
        request_file=args.request_file,
        planning_mode=args.planning_mode,
        output_dir=args.output_dir,
        reference_cases_dir=args.reference_cases_dir,
        data_modules_dir=args.data_modules_dir,
        processed_manifest_path=args.manifest,
        raw_data_dir=args.raw_data_dir,
        processed_data_dir=args.processed_data_dir,
        category_tree_lookup=args.category_tree_lookup,
        stop_after=stop_after,
    )
    _print_cli_summary(result)
    return result.exit_code


def _print_cli_summary(result: PipelineRunResult) -> None:
    if result.error_message and result.exit_code != 0:
        print(result.error_message, file=sys.stderr)
    manifest = result.manifest
    if manifest is not None:
        print(f"planning_mode: {manifest.planning_mode}")
        print(f"case_id: {manifest.case_id}")
        print(f"status: {manifest.status}")
        if manifest.case_config_path:
            print(f"case_config_path: {manifest.case_config_path}")
        if manifest.understanding_spec_path:
            print(f"understanding_spec_path: {manifest.understanding_spec_path}")
        if manifest.module_selection_plan_path:
            print(f"module_selection_plan_path: {manifest.module_selection_plan_path}")
        if manifest.planning_spec_path:
            print(f"planning_spec_path: {manifest.planning_spec_path}")
        if manifest.requirement_workbook_path:
            print(f"requirement_workbook_path: {manifest.requirement_workbook_path}")
    if result.manifest_path is not None:
        print(f"pipeline_manifest_path: {result.manifest_path}")
    if result.exit_code == 0 and manifest and manifest.status == "workbook_generated":
        print("next_step: streamlit run app/streamlit_dashboard.py")
    elif result.exit_code == 0 and manifest and manifest.status == "awaiting_clarification":
        print("next_step: complete clarifying questions in streamlit, then --continue-from-manifest")


if __name__ == "__main__":
    raise SystemExit(main())
