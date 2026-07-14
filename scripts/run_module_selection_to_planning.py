"""Run deterministic ModuleSelectionPlan -> RequirementPlanningSpec adapter."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.case_generation.context_loader import safe_slug
from catemate.core.paths import OUTPUTS_DIR, ensure_project_dirs
from catemate.module_selection.schemas import ModuleSelectionPlan
from catemate.planning.module_selection_adapter import build_planning_spec_from_module_selection
from catemate.understanding.schemas import RequirementUnderstandingSpec


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build RequirementPlanningSpec from understanding + module selection JSON."
    )
    parser.add_argument(
        "--understanding-spec",
        type=Path,
        required=True,
        help="Path to RequirementUnderstandingSpec JSON.",
    )
    parser.add_argument(
        "--module-selection-plan",
        type=Path,
        required=True,
        help="Path to ModuleSelectionPlan JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON path.",
    )
    args = parser.parse_args()

    ensure_project_dirs()

    if not args.understanding_spec.exists():
        print(f"understanding-spec not found: {args.understanding_spec}", file=sys.stderr)
        return 2
    if not args.module_selection_plan.exists():
        print(f"module-selection-plan not found: {args.module_selection_plan}", file=sys.stderr)
        return 2

    try:
        understanding = RequirementUnderstandingSpec.model_validate(
            json.loads(args.understanding_spec.read_text(encoding="utf-8"))
        )
        module_plan = ModuleSelectionPlan.model_validate(
            json.loads(args.module_selection_plan.read_text(encoding="utf-8"))
        )
    except Exception as exc:
        print(f"Failed to load input JSON: {exc}", file=sys.stderr)
        return 2

    planning_spec = build_planning_spec_from_module_selection(
        understanding_spec=understanding,
        module_selection_plan=module_plan,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    case_id = planning_spec.case_id or understanding.case_id or module_plan.case_id
    safe_case_id = safe_slug(case_id, timestamp=timestamp)
    output_path = args.output or (
        OUTPUTS_DIR / f"planning_spec_from_module_selection_{safe_case_id}_{timestamp}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(planning_spec.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    required_count = sum(1 for chart in planning_spec.proposed_charts if not chart.optional)
    optional_count = sum(1 for chart in planning_spec.proposed_charts if chart.optional)

    print(f"case_id: {planning_spec.case_id}")
    print(f"proposed_charts: {len(planning_spec.proposed_charts)}")
    print(f"required charts: {required_count}")
    print(f"optional charts: {optional_count}")
    print(f"source_notes: {len(planning_spec.source_notes)}")
    print(f"warnings: {len(planning_spec.validation_warnings)}")
    print(f"output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
