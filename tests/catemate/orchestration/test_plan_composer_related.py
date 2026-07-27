"""Tests for sub-L3 related plan composition."""

from __future__ import annotations

from catemate.orchestration.blueprint_generator import build_report_blueprint
from catemate.orchestration.plan_composer import compose_analysis_plan
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


def _related_spec() -> RequirementUnderstandingSpec:
    pack = RelatedConceptPack(
        concept_id="smart_pet_bowl",
        display_name="智能宠物碗",
        parent_l3="Bowls & Feeders",
        scope_note="宽定义",
        smart_signals=["smart", "automatic", "fountain"],
        pet_context=["pet", "cat", "dog"],
        boost_terms=["feeder", "dispenser"],
        exclude_terms=["chicken", "slow feed"],
        min_score=0.55,
    )
    return RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="分析菲律宾站智能宠物碗",
        understood=UnderstoodRequirement(
            target_sites=["PH"],
            target_category_text="智能宠物碗",
            inferred_category="Pets > Pet Accessories > Bowls & Feeders",
            inferred_category_candidates=[
                InferredCategoryCandidate(
                    l1="Pets",
                    l2="Pet Accessories",
                    l3="Bowls & Feeders",
                    category_path="Pets > Pet Accessories > Bowls & Feeders",
                )
            ],
            category_level_hint="L3",
            analysis_intents=[AnalysisIntent.TOP_LISTING],
            sub_l3_concept=SubL3Concept(
                is_sub_l3=True,
                concept_id="smart_pet_bowl",
                display_name="智能宠物碗",
                parent_l3="Bowls & Feeders",
            ),
            related_concept_pack=pack,
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def test_blueprint_includes_top_sku_section_for_sub_l3() -> None:
    blueprint = build_report_blueprint(_related_spec())
    section_ids = [section.section_id for section in blueprint.sections]
    assert "s_top_sku" in section_ids


def test_plan_composer_maps_top_sku_to_top_sku_info_module() -> None:
    spec = _related_spec()
    blueprint = build_report_blueprint(spec)
    plan = compose_analysis_plan(blueprint, spec)
    top_sku_runs = [run for run in plan.runs if run.section_id == "s_top_sku"]
    assert len(top_sku_runs) == 1
    run = top_sku_runs[0]
    assert run.module_id == "top_sku_info"
    assert run.grain == "item"
    assert run.table_id == "item_l3_category_csv"
    assert run.is_sub_category is True
    assert run.scope_kind == "subset"
    assert run.related_concept_pack is not None
    assert run.related_concept_pack["concept_id"] == "smart_pet_bowl"
    assert "智能宠物碗" in run.scope_label
    assert run.target_sites == ["PH"]
    assert run.category_l3 == "Bowls & Feeders"
