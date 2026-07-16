"""Tests for RelatedConceptPack generation."""

from __future__ import annotations

from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.understanding.concept_pack_generator import build_fallback_concept_pack
from catemate.understanding.schemas import (
    InferredCategoryCandidate,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    SubL3Concept,
    UnderstandingStatus,
    UnderstoodRequirement,
)


def _spec() -> RequirementUnderstandingSpec:
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
            sub_l3_concept=SubL3Concept(
                is_sub_l3=True,
                concept_id="smart_pet_bowl",
                display_name="智能宠物碗",
                parent_l3="Bowls & Feeders",
            ),
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def test_fallback_concept_pack_has_required_fields() -> None:
    pack = build_fallback_concept_pack(_spec())
    assert isinstance(pack, RelatedConceptPack)
    assert pack.concept_id == "smart_pet_bowl"
    assert pack.display_name == "智能宠物碗"
    assert pack.smart_signals
    assert pack.pet_context
    assert pack.exclude_terms
    assert pack.min_score == 0.55


def test_fallback_includes_site_specific_terms_for_ph() -> None:
    pack = build_fallback_concept_pack(_spec())
    joined = " ".join(pack.smart_signals).lower()
    assert "smart" in joined
    assert "automatic" in joined or "fountain" in joined
