"""Build PPT-ready workbook for the VN Pet Healthcare validation case."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.core.paths import OUTPUTS_DIR, RAW_DATA_DIR
from catemate.modules.pet_healthcare_ppt_ready_workbook import (
    PetHealthcareContext,
    build_pet_healthcare_ppt_ready_workbook,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build VN Pet Healthcare PPT-ready workbook.")
    parser.add_argument("--source", type=Path, default=None, help="Source workbook path.")
    parser.add_argument("--output", type=Path, default=None, help="Output workbook path.")
    args = parser.parse_args()

    source = args.source or RAW_DATA_DIR / "2026 SPH 品类数据看板.xlsx"
    output = args.output or OUTPUTS_DIR / f"ppt_ready_pet_healthcare_vn_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    result = build_pet_healthcare_ppt_ready_workbook(
        PetHealthcareContext(source_workbook_path=source, output_path=output)
    )
    print(f"Generated: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
