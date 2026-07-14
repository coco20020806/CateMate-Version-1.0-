"""Run category requirement workbook generation from a case config YAML."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.config.case_config import load_case_config
from catemate.core.paths import OUTPUTS_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR, ensure_project_dirs
from catemate.modules.category_analysis_data_requirement import build_requirement_workbook
from catemate.schemas.category_requirement import RequirementContext


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate requirement workbook from case config.")
    parser.add_argument("case_config", type=Path, help="Path to a case config YAML file.")
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
        help="Optional output workbook path. Defaults to outputs/category_analysis_data_requirement_<case_id>_<timestamp>.xlsx",
    )
    args = parser.parse_args()

    ensure_project_dirs()
    case_config = load_case_config(args.case_config)

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
        output_path = OUTPUTS_DIR / f"category_analysis_data_requirement_{case_config.case_id}_{timestamp}.xlsx"

    result = build_requirement_workbook(
        context=context,
        raw_data_dir=args.raw_data_dir,
        processed_data_dir=args.processed_data_dir,
        output_path=output_path,
        case_config=case_config,
    )
    print(f"Generated: {result}")


if __name__ == "__main__":
    main()

