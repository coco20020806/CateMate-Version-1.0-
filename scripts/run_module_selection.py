"""Run Module Selection Layer v1 from a RequirementUnderstandingSpec JSON."""

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
from catemate.case_generation.context_loader import safe_slug
from catemate.core.paths import CONFIG_DIR, OUTPUTS_DIR, ensure_project_dirs
from catemate.module_selection.selector import ModuleSelectionSelector
from catemate.module_selection.validator import summarize_module_selection_plan
from catemate.understanding.schemas import RequirementUnderstandingSpec


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate ModuleSelectionPlan JSON from RequirementUnderstandingSpec."
    )
    parser.add_argument(
        "--understanding-spec",
        type=Path,
        required=True,
        help="Path to requirement understanding JSON.",
    )
    parser.add_argument(
        "--data-modules-dir",
        type=Path,
        default=CONFIG_DIR / "data_modules",
        help="Directory of active data module YAML files.",
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

    try:
        understanding = RequirementUnderstandingSpec.model_validate(
            json.loads(args.understanding_spec.read_text(encoding="utf-8"))
        )
    except Exception as exc:
        print(f"Failed to load understanding spec: {exc}", file=sys.stderr)
        return 2

    try:
        settings = AISettings.from_env()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    selector = ModuleSelectionSelector(CateMateAIClient(settings))
    try:
        plan = selector.select(
            understanding,
            data_modules_dir=args.data_modules_dir,
            understanding_spec_path=args.understanding_spec,
        )
    except Exception as exc:
        print(f"Module selection failed: {exc}", file=sys.stderr)
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_case_id = safe_slug(plan.case_id or understanding.case_id, timestamp=timestamp)
    output_path = args.output or (OUTPUTS_DIR / f"module_selection_{safe_case_id}_{timestamp}.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = summarize_module_selection_plan(plan)
    print(f"provider: {settings.provider}")
    print(f"model: {settings.model}")
    print(f"case_id: {summary['case_id']}")
    print(f"status: {summary['status']}")
    print(f"selected: {summary['selected_module_ids']}")
    print(f"optional: {summary['optional_module_ids']}")
    print(f"needs_confirmation: {summary['needs_confirmation_module_ids']}")
    print(f"rejected_count: {summary['rejected_count']}")
    print(f"warnings_count: {summary['warnings_count']}")
    print(f"output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
