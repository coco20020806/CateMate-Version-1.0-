"""Generate a requirement workbook from an existing planning spec JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.config.case_config import load_case_config
from catemate.core.paths import OUTPUTS_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR, ensure_project_dirs
from catemate.modules.category_analysis_data_requirement import (
    build_category_analysis_requirement_spec,
    write_category_analysis_requirement_workbook,
)
from catemate.planning.schemas import RequirementPlanningSpec
from catemate.schemas.category_requirement import RequirementContext


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert RequirementPlanningSpec JSON into a data requirement workbook."
    )
    parser.add_argument(
        "--case-config",
        type=Path,
        required=True,
        help="Path to a case config YAML, e.g. config/cases/pet_healthcare_vn.yaml",
    )
    parser.add_argument(
        "--planning-spec",
        type=Path,
        required=True,
        help="Path to a planning spec JSON produced by run_ai_planning_case.py",
    )
    parser.add_argument(
        "--raw-data-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Path to raw data directory. Defaults to CateMate_rawdata.",
    )
    parser.add_argument(
        "--processed-data-dir",
        type=Path,
        default=PROCESSED_DATA_DIR,
        help="Path to processed data directory. Defaults to CateMate_processeddata.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional workbook output path.",
    )
    args = parser.parse_args()

    ensure_project_dirs()

    if not args.planning_spec.exists():
        print(f"Planning spec not found: {args.planning_spec}", file=sys.stderr)
        return 2

    case_config = load_case_config(args.case_config)
    try:
        payload = json.loads(args.planning_spec.read_text(encoding="utf-8"))
        planning_spec = RequirementPlanningSpec.model_validate(payload)
    except Exception as exc:
        print(f"Invalid planning spec: {exc}", file=sys.stderr)
        return 2

    context = RequirementContext(
        original_request=case_config.original_request,
        target_category_text=case_config.target_category_text,
        business_background=case_config.business_background,
        delivery_audience=case_config.delivery_audience,
        delivery_format=case_config.delivery_format,
        target_sites=case_config.target_sites,
        time_range=case_config.time_range,
    )

    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = (
            OUTPUTS_DIR
            / f"category_analysis_data_requirement_from_planning_{planning_spec.case_id}_{timestamp}.xlsx"
        )

    spec = build_category_analysis_requirement_spec(
        context=context,
        raw_data_dir=args.raw_data_dir,
        processed_data_dir=args.processed_data_dir,
        case_config=case_config,
        planning_spec=planning_spec,
    )
    result = write_category_analysis_requirement_workbook(spec, output_path)

    print(f"case_id: {planning_spec.case_id}")
    print(f"planning_spec: {args.planning_spec}")
    print(f"output: {result}")
    print(f"data_requirement_rows: {len(spec.data_requirements)}")
    print(f"chart_requirement_rows: {len(spec.chart_requirements)}")
    print(f"confirmation_items: {len(spec.confirmation_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
