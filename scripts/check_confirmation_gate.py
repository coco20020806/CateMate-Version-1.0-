"""Check whether a requirement workbook can proceed to PPT-ready generation."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.core.confirmation_gate import evaluate_confirmation_gate
from catemate.core.confirmation_reader import read_confirmation_items
from catemate.core.paths import OUTPUTS_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Check CateMate confirmation gate.")
    parser.add_argument(
        "workbook",
        nargs="?",
        type=Path,
        help="Path to a data requirement / confirmation workbook. Defaults to the latest output workbook.",
    )
    args = parser.parse_args()

    workbook_path = args.workbook or _latest_output_workbook()
    if not workbook_path.exists():
        print(f"Workbook not found: {workbook_path}")
        return 2

    items = read_confirmation_items(workbook_path)
    result = evaluate_confirmation_gate(items)

    print(f"Workbook: {workbook_path}")
    print(result.message)
    print()
    print(f"Confirmation items: {len(items)}")
    for status, count in Counter(item.status for item in items).items():
        print(f"- {status}: {count}")

    if result.blocking_items:
        print()
        print("Blocking items:")
        for idx, item in enumerate(result.blocking_items, start=1):
            suggested = f" | 建议值: {item.suggested_value}" if item.suggested_value else ""
            reason = f" | 原因: {item.reason}" if item.reason else ""
            print(f"{idx}. {item.name} | 状态: {item.status}{suggested}{reason}")
        print()
        print("Next action: 请在确认记录中将上述项目更新为“已确认”或“不需要”；如果补充了数据，请先标记为“已补充”，再由 Agent 复检。")
        return 1

    print()
    print("Next action: 可以进入 PPT-ready workbook 生成步骤。")
    return 0


def _latest_output_workbook() -> Path:
    workbooks = sorted(OUTPUTS_DIR.glob("category_analysis_data_requirement_*.xlsx"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not workbooks:
        raise FileNotFoundError(f"No requirement workbook found in {OUTPUTS_DIR}")
    return workbooks[0]


if __name__ == "__main__":
    raise SystemExit(main())
