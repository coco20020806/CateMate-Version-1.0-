"""Tests for solve loop readiness helpers."""

from __future__ import annotations

from catemate.understanding.schemas import (
    InferredCategoryCandidate,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    SubL3Concept,
    UnderstoodRequirement,
    UnderstandingStatus,
)
from catemate.understanding.solve_loop_readiness import ensure_understanding_ready_for_solve_loop


def _legacy_smart_feeder_spec() -> RequirementUnderstandingSpec:
    return RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="分析一下目前所有站点的智能喂食器，销量如何",
        understood=UnderstoodRequirement(
            target_category_text="智能喂食器",
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
            sub_l3_concept=SubL3Concept(
                is_sub_l3=True,
                concept_id="smart_pet_feeder",
                display_name="智能喂食器",
                parent_l3="Bowls & Feeders",
            ),
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def test_legacy_spec_gets_related_concept_pack() -> None:
    spec = ensure_understanding_ready_for_solve_loop(_legacy_smart_feeder_spec(), ai_client=None)
    assert spec.understood.related_concept_pack is not None
    assert spec.understood.related_concept_pack.concept_id
