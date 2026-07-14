"""Acceptance checks for PPT-ready workbook + HTML preview build."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

FIXTURE_MANIFEST = (
    PROJECT_ROOT
    / "outputs"
    / "runs"
    / "cat_litter_box_ph_20260710_144051"
    / "pipeline_manifest_cat_litter_box_ph_20260710_144051.json"
)
FAILING_CHART_ID = "dashboard_daily_cncb_performance_cncb_site_penetration_latest_month"


def check_bar_overlap_chart_builds() -> None:
    import json

    from catemate.core.paths import PROCESSED_DATA_DIR
    from catemate.planning.schemas import RequirementPlanningSpec
    from catemate.ppt_ready.chart_data_builder import _build_one_sheet, unique_sheet_name
    from catemate.ppt_ready.processed_data_reader import load_processed_manifest

    run_dir = FIXTURE_MANIFEST.parent
    planning_spec = RequirementPlanningSpec.model_validate(
        json.loads(
            (
                run_dir
                / "planning_spec_from_module_selection_cat_litter_box_ph_20260710_144051.json"
            ).read_text(encoding="utf-8")
        )
    )
    manifest = load_processed_manifest(PROCESSED_DATA_DIR / "processed_manifest.yaml")
    chart = next(item for item in planning_spec.proposed_charts if item.chart_id == FAILING_CHART_ID)
    used: set[str] = set()
    sheet = _build_one_sheet(
        chart=chart,
        chart_id=chart.chart_id,
        manifest=manifest,
        processed_data_dir=PROCESSED_DATA_DIR,
        planning_spec=planning_spec,
        used_sheet_names=used,
        project_root=PROJECT_ROOT,
        used_lineage={},
    )
    if sheet.output_status == "unsupported":
        raise AssertionError(f"chart {FAILING_CHART_ID} unexpectedly unsupported")


def check_full_ppt_ready_build() -> None:
    import json

    from catemate.core.paths import PROCESSED_DATA_DIR
    from catemate.ppt_ready.build_from_confirmed import build_ppt_ready_outputs

    if not FIXTURE_MANIFEST.exists():
        raise AssertionError(f"missing fixture manifest: {FIXTURE_MANIFEST}")

    payload = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    workbook = Path(payload["requirement_workbook_path"])
    planning_spec = Path(payload["planning_spec_path"])
    outputs = build_ppt_ready_outputs(
        requirement_workbook=workbook,
        planning_spec_path=planning_spec,
        processed_manifest_path=PROCESSED_DATA_DIR / "processed_manifest.yaml",
        processed_data_dir=PROCESSED_DATA_DIR,
    )
    if not outputs.output_path.exists():
        raise AssertionError("ppt-ready workbook was not written")
    if outputs.html_preview_path is None or not outputs.html_preview_path.exists():
        raise AssertionError("html preview was not written")
    if outputs.sheet_count <= 0:
        raise AssertionError("expected at least one chart sheet")


def main() -> int:
    checks = [
        ("overlap bar chart builds", check_bar_overlap_chart_builds),
        ("full ppt-ready build + html preview", check_full_ppt_ready_build),
    ]
    for name, fn in checks:
        print(f"[RUN] {name}")
        fn()
        print(f"[PASS] {name}")
    print("ALL ACCEPTANCE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
