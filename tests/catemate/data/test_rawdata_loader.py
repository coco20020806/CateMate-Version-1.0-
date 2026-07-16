"""Tests for unified rawdata loading (category / shop / item)."""

from __future__ import annotations

from catemate.data.rawdata_catalog import is_catalog_available
from catemate.data.rawdata_loader import load_rawdata_table, rawdata_available
from catemate.orchestration.catalog_checker import check_plan_catalog_readiness
from catemate.orchestration.schemas import AnalysisPlan, PlanRun
from catemate.scope.executor import execute_scope
from catemate.scope.schemas import ScopeSpec


def test_item_rawdata_available_for_bowls_feeders() -> None:
    assert rawdata_available(
        "item",
        "item_l3_category_csv",
        category_l1="Pets",
        category_l2="Pet Accessories",
        category_l3="Bowls & Feeders",
    )


def test_load_item_l3_category_csv() -> None:
    df, meta = load_rawdata_table(
        "item",
        "item_l3_category_csv",
        category_l1="Pets",
        category_l2="Pet Accessories",
        category_l3="Bowls & Feeders",
    )
    assert meta["source"] == "rawdata_item_csv"
    assert len(df) > 100
    assert "grass_month" in df.columns
    assert "gmv_usd" in df.columns


def test_is_catalog_available_item_requires_category_path() -> None:
    assert not is_catalog_available("item", "item_l3_category_csv")
    assert is_catalog_available(
        "item",
        "item_l3_category_csv",
        category_path=("Pets", "Pet Accessories", "Bowls & Feeders"),
    )


def test_catalog_checker_blocks_shop_missing_rawdata() -> None:
    plan = AnalysisPlan(
        goal="shop trend",
        runs=[
            PlanRun(
                run_id="r1",
                section_id="s_top_shop",
                grain="shop",
                module_id="monthly_market_trend",
                metric_id="gmv",
                table_id="shop_monthly_sales",
                required_catalog="shop/shop_monthly_sales",
                category_l1="Pets",
                category_l2="Pet Accessories",
                category_l3="Bowls & Feeders",
            )
        ],
    )
    updated_plan, questions = check_plan_catalog_readiness(plan)
    assert updated_plan.runs[0].status == "blocked_until_rawdata"
    assert questions
    assert questions[0].grain == "shop"


def test_catalog_checker_blocks_item_without_category_path() -> None:
    plan = AnalysisPlan(
        goal="listing",
        runs=[
            PlanRun(
                run_id="r1",
                section_id="s_top_listing",
                grain="item",
                module_id="top_listing",
                metric_id="gmv",
                table_id="item_l3_category_csv",
                required_catalog="item/item_l3_category_csv",
            )
        ],
    )
    updated_plan, questions = check_plan_catalog_readiness(plan)
    assert updated_plan.runs[0].status == "blocked_until_rawdata"
    assert any("类目映射" in question.question for question in questions)


def test_execute_scope_item_grain_loads_csv() -> None:
    frame = execute_scope(
        ScopeSpec(
            grain="item",
            table_id="item_l3_category_csv",
            category_l1="Pets",
            category_l2="Pet Accessories",
            category_l3="Bowls & Feeders",
            target_sites=["VN"],
        )
    )
    assert len(frame.data) > 0
    assert "Bowls & Feeders" in frame.source_id
