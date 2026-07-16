"""Tests for category confirmation gate."""

from __future__ import annotations

import pytest

from catemate.understanding.category_confirmation import (
    can_confirm_selection,
    confirm_categories,
    finalize_after_category_confirmation,
    initialize_category_positioning,
    is_category_confirmation_complete,
)
from catemate.understanding.schemas import (
    InferredCategoryCandidate,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    UnderstandingStatus,
    UnderstoodRequirement,
)


def _base_spec() -> RequirementUnderstandingSpec:
    return RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="分析菲律宾站智能宠物碗",
        understood=UnderstoodRequirement(target_category_text="智能宠物碗"),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def test_initialize_populates_proposed_candidates() -> None:
    spec = initialize_category_positioning(_base_spec())
    proposed = spec.understood.category_positioning.proposed_candidates
    assert proposed
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
