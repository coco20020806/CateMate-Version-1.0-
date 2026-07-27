"""End-to-end tests for subset vs parent comparison flow."""

from __future__ import annotations

import pytest

from catemate.data.rawdata_loader import rawdata_available
from catemate.execution.runner import execute_analysis_plan
from catemate.orchestration.catalog_checker import check_plan_catalog_readiness
from catemate.orchestration.plan_composer import compose_analysis_plan
from tests.catemate.orchestration.test_plan_composer_sub_l3_scope import (
    _smart_feeder_blueprint,
    _smart_feeder_spec,
)


def _rawdata_ready() -> bool:
    return rawdata_available(
        "item",
        "item_l3_category_csv",
        category_l1="Pets",
        category_l2="Pet Accessories",
        category_l3="Bowls & Feeders",
    ) and rawdata_available("category", "dashboard_history")


def test_comparison_plan_passes_catalog_check() -> None:
    plan = compose_analysis_plan(_smart_feeder_blueprint(), _smart_feeder_spec())
    updated, questions = check_plan_catalog_readiness(plan)
    comparison = next(r for r in updated.runs if r.scope_kind == "comparison")
    assert comparison.status == "executable"
    assert questions == []


def test_comparison_execute_produces_share_table() -> None:
    if not _rawdata_ready():
        pytest.skip("local rawdata unavailable")

    plan = compose_analysis_plan(_smart_feeder_blueprint(), _smart_feeder_spec())
    updated, _ = check_plan_catalog_readiness(plan)
    execution = execute_analysis_plan(updated)
    comparison = next(r for r in updated.runs if r.scope_kind == "comparison")
    share_df = execution.primary_table(
        section_id=comparison.section_id,
        metric_id="gmv",
        table_id="subset_l3_gmv_share_by_site_month",
    )
    assert share_df is not None
    assert not share_df.empty
    assert "gmv_usd_share_of_l3" in share_df.columns
