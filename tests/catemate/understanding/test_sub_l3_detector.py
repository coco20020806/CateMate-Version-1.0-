"""Tests for Sub-L3 detection."""

from __future__ import annotations

from catemate.understanding.schemas import (
    AnalysisIntent,
    InferredCategoryCandidate,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    SubL3Concept,
    UnderstandingStatus,
    UnderstoodRequirement,
)
from catemate.understanding.sub_l3_detector import (
    has_sub_l3_qualifiers,
    infer_sub_l3_concept,
    should_generate_concept_pack,
)


def _spec(
    request: str,
    *,
    l3: str = "Bowls & Feeders",
    is_sub_l3: bool = False,
    category_level_hint: str = "L3",
) -> RequirementUnderstandingSpec:
    return RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request=request,
        understood=UnderstoodRequirement(
            target_sites=["PH"],
            target_category_text="智能宠物碗" if is_sub_l3 else l3,
            inferred_category=f"Pets > Pet Accessories > {l3}",
            inferred_category_candidates=[
                InferredCategoryCandidate(
                    l1="Pets",
                    l2="Pet Accessories",
                    l3=l3,
                    category_path=f"Pets > Pet Accessories > {l3}",
                )
            ],
            category_level_hint=category_level_hint,
            sub_l3_concept=SubL3Concept(
                is_sub_l3=is_sub_l3,
                concept_id="smart_pet_bowl" if is_sub_l3 else "",
                display_name="智能宠物碗" if is_sub_l3 else "",
                parent_l3=l3 if is_sub_l3 else "",
            ),
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def test_has_sub_l3_qualifiers_detects_smart_terms() -> None:
    assert has_sub_l3_qualifiers("分析菲律宾站智能宠物碗")
    assert has_sub_l3_qualifiers("automatic pet water fountain")


def test_has_sub_l3_qualifiers_ignores_plain_category() -> None:
    assert not has_sub_l3_qualifiers("宠物碗")
    assert not has_sub_l3_qualifiers("Bowls & Feeders")


def test_should_generate_when_llm_flags_sub_l3() -> None:
    spec = _spec("分析菲律宾站智能宠物碗", is_sub_l3=True)
    assert should_generate_concept_pack(spec)


def test_should_not_generate_for_plain_l3_request() -> None:
    spec = _spec("分析菲律宾站宠物碗")
    assert not should_generate_concept_pack(spec)


def test_infer_sub_l3_concept_from_request() -> None:
    spec = _spec(
        "分析菲律宾站智能宠物碗",
        is_sub_l3=False,
    )
    spec = spec.model_copy(
        update={
            "understood": spec.understood.model_copy(
                update={"target_category_text": "智能宠物碗"}
            )
        }
    )
    concept = infer_sub_l3_concept(spec)
    assert concept.is_sub_l3
    assert concept.parent_l3 == "Bowls & Feeders"
    assert concept.display_name
