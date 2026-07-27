"""Tests for sub-L3 scope classification in plan composer."""

from __future__ import annotations

from catemate.orchestration.plan_composer import compose_analysis_plan
from catemate.orchestration.schemas import BlueprintSection, ExpectedShape, ReportBlueprint
from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.understanding.schemas import (
    AnalysisIntent,
    InferredCategoryCandidate,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    SubL3Concept,
    UnderstoodRequirement,
    UnderstandingStatus,
)


def _smart_feeder_spec() -> RequirementUnderstandingSpec:
    pack = RelatedConceptPack(
        concept_id="smart_pet_feeding_devices",
        display_name="智能宠物喂养设备",
        parent_l3="Bowls & Feeders",
        scope_note="宽定义",
        smart_signals=["smart", "feeder"],
        pet_context=["pet", "cat"],
        boost_terms=["feeder"],
        exclude_terms=["chicken"],
        min_score=0.55,
    )
    return RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="越南智能喂食器表现",
        understood=UnderstoodRequirement(
            target_sites=["VN"],
            target_category_text="智能喂食器",
            inferred_category="Pets > Pet Accessories > Bowls & Feeders",
            inferred_category_candidates=[
                InferredCategoryCandidate(
                    l1="Pets",
                    l2="Pet Accessories",
                    l3="Bowls & Feeders",
                    category_path="Pets > Pet Accessories > Bowls & Feeders",
                )
            ],
            analysis_intents=[AnalysisIntent.MARKET_TREND, AnalysisIntent.TOP_LISTING],
            sub_l3_concept=SubL3Concept(
                is_sub_l3=True,
                display_name="智能喂食器",
                parent_l3="Bowls & Feeders",
            ),
            related_concept_pack=pack,
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def _smart_feeder_blueprint() -> ReportBlueprint:
    shape = ExpectedShape(
        grain=["grass_region", "grass_month"],
        metrics=["gmv"],
        presentation="trend_table",
    )
    return ReportBlueprint(
        goal="智能喂食器分析",
        sections=[
            BlueprintSection(
                section_id="s_smart_feeder_gmv_trend",
                title="智能喂食器 GMV 趋势",
                sub_question="子集 GMV 趋势",
                module_id="monthly_market_trend",
                metric_id="gmv",
                grain="category",
                expected_shape=shape,
            ),
            BlueprintSection(
                section_id="s_smart_feeder_orders_trend",
                title="智能喂食器 Orders 趋势",
                sub_question="子集 Orders 趋势",
                module_id="monthly_market_trend",
                metric_id="orders",
                grain="category",
                expected_shape=ExpectedShape(
                    grain=["grass_region", "grass_month"],
                    metrics=["orders"],
                    presentation="trend_table",
                ),
            ),
            BlueprintSection(
                section_id="s_top_sku_product_form",
                title="头部 SKU",
                sub_question="头部 SKU",
                module_id="top_sku_info",
                metric_id="gmv",
                grain="item",
                expected_shape=ExpectedShape(
                    grain=["grass_region", "grass_month", "item_name"],
                    metrics=["gmv"],
                    presentation="ranked_table",
                ),
            ),
            BlueprintSection(
                section_id="s_parent_l3_gmv_trend",
                title="父级 L3 GMV 趋势",
                sub_question="父级 L3 趋势",
                module_id="monthly_market_trend",
                metric_id="gmv",
                grain="category",
                expected_shape=shape,
            ),
            BlueprintSection(
                section_id="s_smart_feeder_vs_l3_gmv_share",
                title="智能喂食器占父级 L3 的 GMV 份额",
                sub_question="子集占 L3 GMV 份额",
                module_id="monthly_market_trend",
                metric_id="gmv",
                grain="category",
                expected_shape=ExpectedShape(
                    grain=["grass_region", "grass_month"],
                    metrics=["gmv"],
                    presentation="share_table",
                ),
            ),
        ],
    )


def test_sub_l3_trend_runs_use_item_scope_with_related_pack() -> None:
    plan = compose_analysis_plan(_smart_feeder_blueprint(), _smart_feeder_spec())
    gmv_trend = next(r for r in plan.runs if r.section_id == "s_smart_feeder_gmv_trend")
    assert gmv_trend.is_sub_category is True
    assert gmv_trend.scope_kind == "subset"
    assert gmv_trend.grain == "item"
    assert gmv_trend.table_id == "item_l3_category_csv"
    assert gmv_trend.related_concept_pack is not None


def test_parent_l3_run_uses_category_scope_without_related_pack() -> None:
    plan = compose_analysis_plan(_smart_feeder_blueprint(), _smart_feeder_spec())
    parent = next(r for r in plan.runs if r.section_id == "s_parent_l3_gmv_trend")
    assert parent.is_sub_category is False
    assert parent.scope_kind == "parent_l3"
    assert parent.grain == "category"
    assert parent.table_id == "dashboard_history"
    assert parent.related_concept_pack is None


def test_comparison_run_is_marked_without_sub_category_flag() -> None:
    plan = compose_analysis_plan(_smart_feeder_blueprint(), _smart_feeder_spec())
    comparison = next(r for r in plan.runs if r.section_id == "s_smart_feeder_vs_l3_gmv_share")
    assert comparison.scope_kind == "comparison"
    assert comparison.is_sub_category is False
    assert comparison.source_kind == "computed"
    assert comparison.table_id == "subset_l3_gmv_share_by_site_month"


def test_plan_runs_sorted_subset_parent_comparison() -> None:
    plan = compose_analysis_plan(_smart_feeder_blueprint(), _smart_feeder_spec())
    gmv_runs = [r for r in plan.runs if r.metric_id == "gmv" and r.module_id == "monthly_market_trend"]
    kinds = [r.scope_kind for r in gmv_runs]
    assert kinds.index("subset") < kinds.index("parent_l3") < kinds.index("comparison")


def test_comparison_without_parent_raises() -> None:
    import pytest

    blueprint = ReportBlueprint(
        goal="bad",
        sections=[
            BlueprintSection(
                section_id="s_share_only",
                title="份额",
                sub_question="子集占 L3 份额",
                module_id="monthly_market_trend",
                metric_id="gmv",
                grain="category",
                expected_shape=ExpectedShape(metrics=["gmv"], presentation="share_table"),
            )
        ],
    )
    with pytest.raises(ValueError, match="comparison scope requires subset and parent_l3"):
        compose_analysis_plan(blueprint, _smart_feeder_spec())


def test_subset_gmv_differs_from_parent_gmv_when_data_available() -> None:
    import pytest

    from catemate.core.paths import PROCESSED_DATA_DIR
    from catemate.execution.runner import execute_analysis_plan
    from catemate.orchestration.schemas import AnalysisPlan

    if not PROCESSED_DATA_DIR.exists():
        pytest.skip("processed data unavailable")

    plan = compose_analysis_plan(_smart_feeder_blueprint(), _smart_feeder_spec())
    subset_run = next(r for r in plan.runs if r.section_id == "s_smart_feeder_gmv_trend")
    parent_run = next(r for r in plan.runs if r.section_id == "s_parent_l3_gmv_trend")
    mini_plan = AnalysisPlan(goal=plan.goal, runs=[subset_run, parent_run], loop_iteration=plan.loop_iteration)
    execution = execute_analysis_plan(mini_plan, processed_data_dir=PROCESSED_DATA_DIR)
    subset_df = execution.primary_table(
        section_id=subset_run.section_id,
        metric_id="gmv",
        table_id="gmv_by_site_month",
    )
    parent_df = execution.primary_table(
        section_id=parent_run.section_id,
        metric_id="gmv",
        table_id="gmv_by_site_month",
    )
    assert subset_df is not None and parent_df is not None
    subset_total = float(subset_df["gmv_usd"].sum())
    parent_total = float(parent_df["gmv_usd"].sum())
    assert subset_total < parent_total
    assert subset_total > 0
