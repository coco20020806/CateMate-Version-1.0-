"""Integration tests for ensure + plan compose on sub-L3 specs."""

from __future__ import annotations

from catemate.orchestration.plan_composer import compose_analysis_plan
from catemate.orchestration.schemas import BlueprintSection, ExpectedShape, ReportBlueprint
from catemate.understanding.schemas import (
    InferredCategoryCandidate,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    SubL3Concept,
    UnderstoodRequirement,
    UnderstandingStatus,
)
from catemate.understanding.solve_loop_readiness import ensure_understanding_ready_for_solve_loop


def test_legacy_smart_feeder_compose_subset_runs() -> None:
    spec = RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="分析一下目前所有站点的智能喂食器，销量如何",
        understood=UnderstoodRequirement(
            target_category_text="智能喂食器",
            inferred_category_candidates=[
                InferredCategoryCandidate(
                    l1="Pets",
                    l2="Pet Accessories",
                    l3="Bowls & Feeders",
                    category_path="Pets > Pet Accessories > Bowls & Feeders",
                )
            ],
            sub_l3_concept=SubL3Concept(
                is_sub_l3=True,
                concept_id="smart_pet_feeder",
                display_name="智能喂食器",
                parent_l3="Bowls & Feeders",
            ),
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )
    ready = ensure_understanding_ready_for_solve_loop(spec, ai_client=None)
    blueprint = ReportBlueprint(
        goal="智能喂食器分析",
        sections=[
            BlueprintSection(
                section_id="s_smart_feeder_orders_trend",
                title="智能喂食器销量趋势",
                sub_question="子集销量趋势",
                module_id="monthly_market_trend",
                metric_id="orders",
                grain="item",
                expected_shape=ExpectedShape(
                    grain=["grass_region", "grass_month"],
                    metrics=["orders"],
                    presentation="trend_table",
                ),
            ),
            BlueprintSection(
                section_id="s_parent_l3_orders_trend",
                title="父级 L3 销量趋势",
                sub_question="父级趋势",
                module_id="monthly_market_trend",
                metric_id="orders",
                grain="category",
                expected_shape=ExpectedShape(
                    grain=["grass_region", "grass_month"],
                    metrics=["orders"],
                    presentation="trend_table",
                ),
            ),
        ],
    )
    plan = compose_analysis_plan(blueprint, ready)
    subset = next(r for r in plan.runs if r.section_id == "s_smart_feeder_orders_trend")
    parent = next(r for r in plan.runs if r.section_id == "s_parent_l3_orders_trend")
    assert subset.scope_kind == "subset"
    assert subset.grain == "item"
    assert subset.related_concept_pack is not None
    assert parent.scope_kind == "parent_l3"
    assert parent.grain == "category"
