"""Validate RequirementPlanningSpec consistency against ModuleSelectionPlan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.module_selection.schemas import ModuleSelectionPlan
from catemate.planning.module_selection_adapter import (
    has_serious_validation_issues,
    validate_planning_spec_against_module_selection,
)
from catemate.planning.schemas import RequirementPlanningSpec


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate planning spec generated from module selection."
    )
    parser.add_argument(
        "--planning-spec",
        type=Path,
        required=True,
        help="Path to RequirementPlanningSpec JSON.",
    )
    parser.add_argument(
        "--module-selection-plan",
        type=Path,
        required=True,
        help="Path to ModuleSelectionPlan JSON.",
    )
    args = parser.parse_args()

    if not args.planning_spec.exists():
        print(f"planning-spec not found: {args.planning_spec}", file=sys.stderr)
        return 2
    if not args.module_selection_plan.exists():
        print(f"module-selection-plan not found: {args.module_selection_plan}", file=sys.stderr)
        return 2

    try:
        planning_spec = RequirementPlanningSpec.model_validate(
            json.loads(args.planning_spec.read_text(encoding="utf-8"))
        )
        module_plan = ModuleSelectionPlan.model_validate(
            json.loads(args.module_selection_plan.read_text(encoding="utf-8"))
        )
    except Exception as exc:
        print(f"Failed to load input JSON: {exc}", file=sys.stderr)
        return 2

    issues = validate_planning_spec_against_module_selection(planning_spec, module_plan)
    warnings = [item for item in issues if not item.startswith("SERIOUS:")]
    errors = [item for item in issues if item.startswith("SERIOUS:")]

    print(f"case_id: {planning_spec.case_id}")
    print(f"warnings: {len(warnings)}")
    print(f"errors: {len(errors)}")

    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}")

    if has_serious_validation_issues(issues):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
