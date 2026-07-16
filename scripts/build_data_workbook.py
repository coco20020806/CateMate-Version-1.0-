"""CLI: build Data Workbook from solve loop state JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.execution.runner import execute_analysis_plan
from catemate.modules.data_workbook import write_data_workbook
from catemate.orchestration.schemas import SolveLoopState


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Data Workbook from solve loop state.")
    parser.add_argument("--state", type=Path, required=True, help="solve_loop_state JSON path")
    parser.add_argument("--output", type=Path, required=True, help="Output xlsx path")
    args = parser.parse_args()

    payload = json.loads(args.state.read_text(encoding="utf-8"))
    state = SolveLoopState.model_validate(payload)
    if state.plan is None:
        raise SystemExit("Solve loop state missing plan")

    execution = execute_analysis_plan(state.plan)
    write_data_workbook(state=state, execution=execution, output_path=args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
