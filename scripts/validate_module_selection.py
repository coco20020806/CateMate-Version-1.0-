"""Validate and summarize a ModuleSelectionPlan against active data modules."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.module_selection.context import build_module_registry, load_active_data_modules
from catemate.module_selection.schemas import (
    ChartRuleSource,
    ModuleDecision,
    ModuleSelectionItem,
    ModuleSelectionPlan,
    SelectedChartIntent,
    SelectionConfidence,
)
from catemate.module_selection.validator import (
    summarize_module_selection_plan,
    validate_and_normalize_module_selection_plan,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ModuleSelectionPlan JSON.")
    parser.add_argument("--module-selection-plan", type=Path, required=True)
    parser.add_argument(
        "--data-modules-dir",
        type=Path,
        default=PROJECT_ROOT / "config" / "data_modules",
    )
    args = parser.parse_args()

    if not args.module_selection_plan.exists():
        print(f"plan not found: {args.module_selection_plan}", file=sys.stderr)
        return 2

    try:
        plan = ModuleSelectionPlan.model_validate(
            json.loads(args.module_selection_plan.read_text(encoding="utf-8"))
        )
        modules = load_active_data_modules(args.data_modules_dir)
        registry = build_module_registry(modules)
        normalized = validate_and_normalize_module_selection_plan(plan, registry)
    except Exception as exc:
        print(f"Schema/validation error: {exc}", file=sys.stderr)
        return 1

    active_count = len(registry)
    covered = {item.module_id for item in normalized.all_items()}
    unknown = [item.module_id for item in plan.all_items() if item.module_id not in registry]

    print(f"active module count: {active_count}")
    print(f"covered module count: {len(covered)}")
    print(f"unknown modules: {unknown}")
    print(f"warnings: {normalized.global_warnings}")
    summary = summarize_module_selection_plan(normalized)
    print(f"selected chart intents: {summary['selected_chart_intents']}")
    return 0


def run_unit_tests() -> None:
    """Lightweight validator tests without pytest."""
    modules = load_active_data_modules(PROJECT_ROOT / "config" / "data_modules")
    registry = build_module_registry(modules)
    active_ids = set(registry)

    # missing modules auto-rejected
    partial = ModuleSelectionPlan(
        case_id="test",
        status="ready",
        original_request="test",
        selected_modules=[
            ModuleSelectionItem(
                module_id="dashboard_top_listing",
                decision=ModuleDecision.SELECTED,
                reason="top listing",
                source_tables=[],
                selected_chart_intents=[],
            )
        ],
    )
    normalized = validate_and_normalize_module_selection_plan(partial, registry)
    covered = {item.module_id for item in normalized.all_items()}
    assert covered == active_ids
    assert len(normalized.rejected_modules) >= 6
    print("missing modules auto-rejected: OK")

    # auto-fill source_tables
    empty_tables = ModuleSelectionPlan(
        case_id="test2",
        status="ready",
        original_request="trend",
        selected_modules=[
            ModuleSelectionItem(
                module_id="rm_monthly_category_performance",
                decision=ModuleDecision.SELECTED,
                reason="trend",
                source_tables=[],
                selected_chart_intents=[
                    SelectedChartIntent(
                        chart_intent="monthly_trend",
                        chart_type="trend",
                        rule_source=ChartRuleSource.MODULE_DEFAULT,
                    )
                ],
            )
        ],
        rejected_modules=[
            ModuleSelectionItem(
                module_id=mid,
                decision=ModuleDecision.REJECTED,
                reason="not needed",
            )
            for mid in active_ids
            if mid != "rm_monthly_category_performance"
        ],
    )
    normalized2 = validate_and_normalize_module_selection_plan(empty_tables, registry)
    selected = normalized2.selected_modules[0]
    assert selected.source_tables == ["rm_raw_data"]
    assert selected.selected_chart_intents
    assert selected.selected_chart_intents[0].x_axis == "grass_month"
    print("source_tables + default chart merge: OK")

    # unknown module warning
    unknown_plan = ModuleSelectionPlan(
        case_id="test3",
        status="ready",
        original_request="x",
        selected_modules=[
            ModuleSelectionItem(
                module_id="fake_module",
                decision=ModuleDecision.SELECTED,
                reason="fake",
            )
        ],
    )
    normalized3 = validate_and_normalize_module_selection_plan(unknown_plan, registry)
    assert any("fake_module" in w for w in normalized3.global_warnings)
    assert "fake_module" not in {i.module_id for i in normalized3.all_items()}
    print("unknown module warning: OK")

    # schema sample
    ModuleSelectionPlan.model_validate(
        {
            "case_id": "sample",
            "status": "ready",
            "original_request": "sample",
            "selected_modules": [],
            "rejected_modules": [
                {
                    "module_id": mid,
                    "decision": "rejected",
                    "reason": "none",
                }
                for mid in sorted(active_ids)
            ],
        }
    )
    print("schema sample validate: OK")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_unit_tests()
        print("all validator unit tests: OK")
        raise SystemExit(0)
    raise SystemExit(main())
