"""Export Plan sheet snapshot for a run using current plan_composer."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.execution.result_collector import ExecutionResult
from catemate.modules.data_workbook import build_data_workbook_spec
from catemate.orchestration.module_registry import is_active_v2_module
from catemate.orchestration.plan_composer import compose_analysis_plan
from catemate.orchestration.schemas import ReportBlueprint, SolveVerdict
from catemate.understanding.schemas import RequirementUnderstandingSpec

ACTIVE_MODULES = {"monthly_market_trend", "top_sku_info"}
PLAN_HEADERS = [
    "run_id",
    "section_id",
    "module_id",
    "metric_id",
    "grain",
    "is_sub_category",
    "scope_kind",
    "table_id",
    "status",
    "scope_label",
    "missing",
]


def export_plan_snapshot(run_dir: Path) -> tuple[Path, Path]:
    understanding_path = next(run_dir.glob("requirement_understanding_*.json"))
    blueprint_path = next(run_dir.glob("report_blueprint_*.json"))
    verdict_path = next(run_dir.glob("solve_verdict_*.json"), None)

    understanding = RequirementUnderstandingSpec.model_validate(
        json.loads(understanding_path.read_text(encoding="utf-8"))
    )
    blueprint = ReportBlueprint.model_validate(json.loads(blueprint_path.read_text(encoding="utf-8")))
    verdict = (
        SolveVerdict.model_validate(json.loads(verdict_path.read_text(encoding="utf-8")))
        if verdict_path is not None
        else SolveVerdict(verdict="partial")
    )

    sections = [
        section
        for section in blueprint.sections
        if section.module_id in ACTIVE_MODULES and is_active_v2_module(section.module_id)
    ]
    filtered_blueprint = blueprint.model_copy(update={"sections": sections})
    plan = compose_analysis_plan(filtered_blueprint, understanding)
    spec = build_data_workbook_spec(
        blueprint=filtered_blueprint,
        plan=plan,
        verdict=verdict,
        execution=ExecutionResult(),
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = run_dir / f"plan_snapshot_{stamp}.json"
    csv_path = run_dir / f"plan_snapshot_{stamp}.csv"

    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_run": run_dir.name,
        "original_request": understanding.original_request,
        "goal": plan.goal,
        "plan_headers": PLAN_HEADERS,
        "runs": [row.model_dump(mode="json") for row in spec.plan_rows],
        "analysis_plan_runs": [run.model_dump(mode="json") for run in plan.runs],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(PLAN_HEADERS)
        for row in spec.plan_rows:
            writer.writerow([getattr(row, header) for header in PLAN_HEADERS])

    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Plan sheet snapshot for a pipeline run.")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "runs" / "smart_pet_bowl_sg_20260716_154654",
        help="Run directory containing understanding + blueprint JSON files.",
    )
    args = parser.parse_args()
    json_path, csv_path = export_plan_snapshot(args.run_dir.resolve())
    print(f"plan_snapshot_json: {json_path}")
    print(f"plan_snapshot_csv: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
