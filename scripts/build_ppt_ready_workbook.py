"""Build a PPT-ready workbook from a confirmed requirement workbook."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.core.paths import OUTPUTS_DIR, RAW_DATA_DIR
from catemate.modules.ppt_ready_workbook import PptReadyContext, build_ppt_ready_workbook


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CateMate PPT-ready workbook.")
    parser.add_argument("confirmed_workbook", type=Path, help="Confirmed data requirement workbook.")
    parser.add_argument("--raw-workbook", type=Path, default=None, help="SPH source workbook. Defaults to the first SPH RM file.")
    parser.add_argument("--output", type=Path, default=None, help="Output PPT-ready workbook path.")
    args = parser.parse_args()

    raw_workbook = args.raw_workbook or _default_raw_workbook()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output or OUTPUTS_DIR / f"ppt_ready_workbook_{timestamp}.xlsx"

    result = build_ppt_ready_workbook(
        PptReadyContext(
            confirmed_workbook_path=args.confirmed_workbook,
            raw_workbook_path=raw_workbook,
            output_path=output,
        )
    )
    print(f"Generated: {result}")
    return 0


def _default_raw_workbook() -> Path:
    candidates = sorted(RAW_DATA_DIR.glob("SPH*RM*.xlsx"))
    if not candidates:
        raise FileNotFoundError(f"No SPH RM workbook found in {RAW_DATA_DIR}")
    return candidates[0]


if __name__ == "__main__":
    raise SystemExit(main())
