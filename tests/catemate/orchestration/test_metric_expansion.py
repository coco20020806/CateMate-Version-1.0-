"""Tests for Plan A supplementary metric expansion."""

from __future__ import annotations

from catemate.orchestration.blueprint_generator import build_report_blueprint
from catemate.orchestration.metric_advisor import recommend_supplementary_metrics
from catemate.orchestration.module_capability import (
    available_metrics_for_module,
    filter_metrics_by_columns,
    list_module_metrics,
)
from catemate.orchestration.plan_composer import compose_analysis_plan
from catemate.orchestration.plan_expander import expand_plan_with_metrics
from catemate.orchestration.schemas import MetricRecommendation
from catemate.orchestration.solve_loop import run_solve_loop
from catemate.understanding.schemas import (
    AnalysisIntent,
    InferredCategoryCandidate,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    UnderstoodRequirement,
    UnderstandingStatus,
)


def test_list_module_metrics_monthly_market_trend() -> None:
    metrics = list_module_metrics("monthly_market_trend")
    assert "gmv" in metrics
    assert "orders" in metrics


def test_filter_metrics_by_columns_orders() -> None:
    columns = [
        "grass_region",
        "grass_month",
        "gmv_usd",
        "orders",
    ]
    filtered = filter_metrics_by_columns(["gmv", "orders", "aov"], columns)
    assert filtered == ["gmv", "orders", "aov"]


def test_available_metrics_for_module() -> None:
    columns = ["grass_region", "grass_month", "gmv_usd", "orders"]
    assert available_metrics_for_module("monthly_market_trend", columns) == [
        "gmv",
        "orders",
        "aov",
    ]


def _pet_bowls_spec() -> RequirementUnderstandingSpec:
    return RequirementUnderstandingSpec(
        case_id="pet_bowls",
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="我想看看宠物碗的类目大趋势",
        understood=UnderstoodRequirement(
            target_category_text="宠物碗",
            inferred_category="Pets > Pet Accessories > Bowls & Feeders",
            inferred_category_candidates=[
                InferredCategoryCandidate(
                    l1="Pets",
                    l2="Pet Accessories",
                    l3="Bowls & Feeders",
                    category_path="Pets > Pet Accessories > Bowls & Feeders",
                    reason="match",
                )
            ],
            analysis_intents=[AnalysisIntent.MARKET_TREND],
            metric_definitions={
                "market_trend": "观察销售额、销量、商品数随时间变化的大趋势",
            },
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def test_metric_advisor_rules_recommend_orders() -> None:
    spec = _pet_bowls_spec()
    blueprint = build_report_blueprint(spec)
    plan = compose_analysis_plan(blueprint, spec)
    run = plan.runs[0]
    recommendations = recommend_supplementary_metrics(
        understanding=spec,
        blueprint=blueprint,
        plan=plan,
        executed_keys={f"{run.section_id}:{run.metric_id}"},
        available_by_run={run.run_id: ["gmv", "orders"]},
        ai_client=None,
    )
    assert recommendations
    assert recommendations[0].metric_id == "orders"
    assert recommendations[0].section_id == "s_market_trend"


def test_plan_expander_same_section() -> None:
    spec = _pet_bowls_spec()
    blueprint = build_report_blueprint(spec)
    plan = compose_analysis_plan(blueprint, spec)
    updated_plan, updated_blueprint = expand_plan_with_metrics(
        plan,
        blueprint,
        [
            MetricRecommendation(
                section_id="s_market_trend",
                metric_id="orders",
                role="supplementary",
                reason="辅助判断趋势",
            )
        ],
    )
    assert len(updated_plan.runs) == 2
    assert updated_plan.runs[0].section_id == "s_market_trend"
    assert updated_plan.runs[1].section_id == "s_market_trend"
    assert updated_plan.runs[1].metric_id == "orders"
    assert updated_plan.runs[0].grain == updated_plan.runs[1].grain
    assert updated_plan.runs[0].table_id == updated_plan.runs[1].table_id
    assert "orders" in updated_blueprint.sections[0].expected_shape.metrics


def test_solve_loop_metric_expansion_produces_orders_tables() -> None:
    spec = _pet_bowls_spec()
    result = run_solve_loop(spec, max_iterations=1, ai_client=None)
    state = result.state
    assert state.verdict is not None
    assert state.verdict.verdict == "solved"
    assert state.plan is not None
    metric_ids = {run.metric_id for run in state.plan.runs}
    assert metric_ids == {"gmv", "orders"}
    recommendations = state.metadata.get("metric_recommendations") or []
    assert recommendations
    assert recommendations[0]["metric_id"] == "orders"


def test_gmv_only_request_skips_orders_expansion() -> None:
    spec = RequirementUnderstandingSpec(
        case_id="gmv_only",
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="仅分析 SG 文具类目 GMV，不要 orders",
        understood=UnderstoodRequirement(
            target_sites=["SG"],
            target_category_text="Stationery",
            inferred_category_candidates=[
                InferredCategoryCandidate(
                    l1="Stationery",
                    l2="Notebooks & Papers",
                    category_path="Stationery > Notebooks & Papers",
                    reason="match",
                )
            ],
            analysis_intents=[AnalysisIntent.MARKET_TREND],
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )
    result = run_solve_loop(spec, max_iterations=1, ai_client=None)
    state = result.state
    assert state.plan is not None
    assert len(state.plan.runs) == 1
    assert state.plan.runs[0].metric_id == "gmv"
