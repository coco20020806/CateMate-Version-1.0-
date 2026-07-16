"""Tests for category confirmation gate."""

from __future__ import annotations

from typing import Any

import pytest

from catemate.understanding.category_confirmation import (
    apply_category_feedback,
    can_confirm_selection,
    confirm_categories,
    finalize_after_category_confirmation,
    initialize_category_positioning,
    is_category_confirmation_complete,
)
from catemate.understanding.schemas import (
    ConfidenceLevel,
    InferredCategoryCandidate,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    UnderstandingStatus,
    UnderstoodRequirement,
)


class _MockAIClient:
    def complete_json(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "spec_version": "requirement_understanding_v1",
            "case_id": "smart_pet_bowl",
            "status": "ready_for_module_selection",
            "original_request": "新加坡和越南市场的智能宠物碗的类目趋势与产品概括",
            "conversation_summary": "用户确认类目为 Bowls & Feeders。",
            "understood": {
                "target_category_text": "智能宠物碗",
                "inferred_category": "Pets > Pet Accessories > Bowls & Feeders",
                "inferred_category_candidates": [
                    {
                        "l1": "Pets",
                        "l2": "Pet Accessories",
                        "l3": "Bowls & Feeders",
                        "category_path": "Pets > Pet Accessories > Bowls & Feeders",
                        "reason": "用户反馈确认",
                        "confidence": "high",
                    }
                ],
                "category_level_hint": "L3",
                "analysis_intents": ["market_trend"],
            },
            "readiness": {
                "can_select_modules": True,
                "blocking_reasons": [],
                "non_blocking_notes": [],
            },
        }


def _base_spec() -> RequirementUnderstandingSpec:
    return RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="新加坡和越南市场的智能宠物碗的类目趋势与产品概括",
        understood=UnderstoodRequirement(target_category_text="智能宠物碗"),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def test_initialize_populates_bowls_and_feeders_first() -> None:
    spec = initialize_category_positioning(_base_spec())
    proposed = spec.understood.category_positioning.proposed_candidates
    assert proposed
    assert proposed[0].category_path == "Pets > Pet Accessories > Bowls & Feeders"
    assert spec.understood.category_positioning.positioning_type == "single_category"
    assert not spec.understood.category_positioning.confirmed


def test_confirm_requires_at_least_one_selection() -> None:
    spec = initialize_category_positioning(_base_spec())
    path = spec.understood.category_positioning.proposed_candidates[0].category_path
    confirmed = confirm_categories(spec, [path])
    assert confirmed.understood.category_positioning.confirmed
    assert is_category_confirmation_complete(confirmed)


def test_confirm_rejects_empty_selection() -> None:
    spec = initialize_category_positioning(_base_spec())
    with pytest.raises(ValueError, match="至少勾选"):
        confirm_categories(spec, [])


def test_can_confirm_selection() -> None:
    assert not can_confirm_selection([])
    assert can_confirm_selection(["Pets > Pet Accessories > Bowls & Feeders"])


def test_finalize_sets_inferred_after_confirm() -> None:
    spec = initialize_category_positioning(_base_spec())
    path = spec.understood.category_positioning.proposed_candidates[0].category_path
    spec = confirm_categories(spec, [path])
    finalized = finalize_after_category_confirmation(spec, ai_client=None)
    assert finalized.understood.inferred_category_candidates
    assert finalized.understood.inferred_category


def test_legacy_spec_without_gate_treated_as_complete() -> None:
    spec = RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="test",
        understood=UnderstoodRequirement(
            inferred_category_candidates=[
                InferredCategoryCandidate(
                    l1="Pets",
                    l2="Pet Accessories",
                    l3="Bowls & Feeders",
                    category_path="Pets > Pet Accessories > Bowls & Feeders",
                )
            ]
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )
    assert is_category_confirmation_complete(spec)


def test_apply_category_feedback_updates_proposed_candidates() -> None:
    spec = initialize_category_positioning(_base_spec())
    wrong = InferredCategoryCandidate(
        l1="Pets",
        l2="Pet Healthcare",
        l3="Medication",
        category_path="Pets > Pet Healthcare > Medication",
        confidence=ConfidenceLevel.HIGH,
    )
    positioning = spec.understood.category_positioning.model_copy(
        update={"proposed_candidates": [wrong] * 5}
    )
    spec = spec.model_copy(
        update={"understood": spec.understood.model_copy(update={"category_positioning": positioning})}
    )

    updated = apply_category_feedback(
        spec,
        "应该是 L3 类目 Bowls & Feeders",
        ai_client=_MockAIClient(),
    )
    proposed = updated.understood.category_positioning.proposed_candidates
    assert proposed
    assert proposed[0].category_path == "Pets > Pet Accessories > Bowls & Feeders"
    assert "Healthcare" not in proposed[0].category_path
    assert "Bowls & Feeders" in updated.understood.category_positioning.feedback_rounds[-1].system_summary
