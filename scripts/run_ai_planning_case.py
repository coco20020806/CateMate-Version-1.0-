"""Run AI planning for a CateMate case config and save RequirementPlanningSpec JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.ai.client import CateMateAIClient
from catemate.ai.settings import AISettings
from catemate.core.paths import CONFIG_DIR, OUTPUTS_DIR, PROCESSED_DATA_DIR, ensure_project_dirs
from catemate.planning.context_loader import build_planning_context
from catemate.planning.planner import RequirementPlanner


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate CateMate AI planning spec JSON.")
    parser.add_argument(
        "--case-config",
        type=Path,
        required=True,
        help="Path to a case config YAML, e.g. config/cases/pet_healthcare_vn.yaml",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROCESSED_DATA_DIR / "processed_manifest.yaml",
        help="Path to processed_manifest.yaml",
    )
    parser.add_argument(
        "--data-modules-dir",
        type=Path,
        default=CONFIG_DIR / "data_modules",
        help="Directory containing data module YAML configs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON path. Defaults to outputs/planning_spec_<case_id>_<timestamp>.json",
    )
    args = parser.parse_args()

    ensure_project_dirs()

    try:
        settings = AISettings.from_env()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        context = build_planning_context(
            case_config_path=args.case_config,
            manifest_path=args.manifest,
            data_modules_dir=args.data_modules_dir,
        )
    except Exception as exc:
        print(f"Context load error: {exc}", file=sys.stderr)
        return 2

    client = CateMateAIClient(settings)
    planner = RequirementPlanner(client)

    try:
        spec = planner.plan(context)
    except Exception as exc:
        print(f"Planning failed: {exc}", file=sys.stderr)
        return 1

    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUTS_DIR / f"planning_spec_{spec.case_id}_{timestamp}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(spec.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"provider: {settings.provider}")
    print(f"model: {settings.model}")
    print(f"case_id: {spec.case_id}")
    print(f"output: {output_path}")
    print(f"matched_modules: {len(spec.matched_data_modules)}")
    print(f"proposed_charts: {len(spec.proposed_charts)}")
    print(f"missing_questions: {len(spec.missing_data_questions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
