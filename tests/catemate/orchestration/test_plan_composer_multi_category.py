"""Tests for multi-category plan composition."""

from __future__ import annotations

from catemate.orchestration.blueprint_generator import build_report_blueprint
from catemate.orchestration.plan_composer import compose_analysis_plan
from catemate.understanding.schemas import (
    AnalysisIntent,
    CategoryPositioning,
    InferredCategoryCandidate,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    UnderstoodRequirement,
    UnderstandingStatus,
)


def _multi_spec() -> RequirementUnderstandingSpec:
    cat_a = InferredCategoryCandidate(
        l1="Pets",
        l2="Pet Accessories",
        l3="Bowls & Feeders",
        category_path="Pets > Pet Accessories > Bowls & Feeders",
    )
    cat_b = InferredCategoryCandidate(
        l1="Pets",
        l2="Pet Food",
        l3="Dog Food",
        category_path="Pets > Pet Food > Dog Food",
    )
    return RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="分析宠物碗和狗粮",
        understood=UnderstoodRequirement(
            target_sites=["PH"],
            analysis_intents=[AnalysisIntent.MARKET_TREND],
            inferred_category="Pets > Pet Accessories > Bowls & Feeders | Pets > Pet Food > Dog Food",
            inferred_category_candidates=[cat_a, cat_b],
            category_positioning=CategoryPositioning(
                positioning_type="multi_category",
                proposed_candidates=[cat_a, cat_b],
                confirmed_candidates=[cat_a, cat_b],
                confirmed=True,
            ),
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def test_multi_category_generates_runs_per_candidate() -> None:
    spec = _multi_spec()
    blueprint = build_report_blueprint(spec)
    plan = compose_analysis_plan(blueprint, spec)
    assert len(plan.runs) == len(blueprint.sections) * 2
    l3_values = {run.category_l3 for run in plan.runs}
    assert "Bowls & Feeders" in l3_values
    assert "Dog Food" in l3_values
