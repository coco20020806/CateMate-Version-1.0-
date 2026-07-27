"""Tests for catalog_checker handling of comparison derived tables."""

from __future__ import annotations

from catemate.orchestration.catalog_checker import check_plan_catalog_readiness
from catemate.orchestration.schemas import AnalysisPlan, PlanRun


def test_comparison_run_is_executable_without_rawdata_question() -> None:
    plan = AnalysisPlan(
        goal="subset vs L3",
        runs=[
            PlanRun(
                run_id="r1",
                section_id="s_share",
                grain="category",
                module_id="monthly_market_trend",
                metric_id="gmv",
                table_id="subset_l3_gmv_share_by_site_month",
                required_catalog="category/subset_l3_gmv_share_by_site_month",
                scope_kind="comparison",
            )
        ],
    )
    updated_plan, questions = check_plan_catalog_readiness(plan)
    assert updated_plan.runs[0].status == "executable"
    assert questions == []
