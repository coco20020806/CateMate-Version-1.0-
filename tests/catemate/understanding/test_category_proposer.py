"""Tests for category proposer."""

from __future__ import annotations

from catemate.understanding.category_proposer import (
    derive_positioning_type,
    merge_candidates,
    prune_ancestor_candidates,
    propose_category_candidates,
)
from catemate.understanding.schemas import ConfidenceLevel, InferredCategoryCandidate


def test_propose_smart_pet_bowl_maps_to_bowls_and_feeders() -> None:
    candidates = propose_category_candidates(
        request_text="新加坡和越南市场的智能宠物碗的类目趋势与产品概括",
        category_text="智能宠物碗",
    )
    assert candidates
    assert candidates[0].category_path == "Pets > Pet Accessories > Bowls & Feeders"
    paths = [candidate.category_path for candidate in candidates]
    assert "Pets > Pet Healthcare" not in paths
    assert "Pets" not in paths
    assert derive_positioning_type(candidates) == "single_category"


def test_propose_returns_candidates_for_pet_bowl_request() -> None:
    candidates = propose_category_candidates(
        request_text="分析菲律宾站智能宠物碗",
        category_text="智能宠物碗",
    )
    assert candidates
    paths = [c.category_path for c in candidates]
    assert any("Bowls" in path or "Feeder" in path for path in paths)


def test_ancestor_pruning_drops_l1_l2_when_l3_present() -> None:
    l3 = InferredCategoryCandidate(
        l1="Pets",
        l2="Pet Accessories",
        l3="Bowls & Feeders",
        category_path="Pets > Pet Accessories > Bowls & Feeders",
        confidence=ConfidenceLevel.HIGH,
    )
    l1 = InferredCategoryCandidate(
        l1="Pets",
        category_path="Pets",
        confidence=ConfidenceLevel.MEDIUM,
    )
    l2 = InferredCategoryCandidate(
        l1="Pets",
        l2="Pet Accessories",
        category_path="Pets > Pet Accessories",
        confidence=ConfidenceLevel.MEDIUM,
    )
    pruned = prune_ancestor_candidates([l3, l1, l2])
    assert [item.category_path for item in pruned] == ["Pets > Pet Accessories > Bowls & Feeders"]


def test_multi_l3_candidates_keep_non_ancestor_paths() -> None:
    dog_food = InferredCategoryCandidate(
        l1="Pets",
        l2="Pet Food",
        l3="Dog Food",
        category_path="Pets > Pet Food > Dog Food",
        confidence=ConfidenceLevel.HIGH,
    )
    cat_food = InferredCategoryCandidate(
        l1="Pets",
        l2="Pet Food",
        l3="Cat Food",
        category_path="Pets > Pet Food > Cat Food",
        confidence=ConfidenceLevel.HIGH,
    )
    pruned = prune_ancestor_candidates([dog_food, cat_food])
    assert len(pruned) == 2


def test_merge_candidates_prefers_primary_order() -> None:
    primary = [
        InferredCategoryCandidate(
            l1="Pets",
            l2="Pet Accessories",
            l3="Bowls & Feeders",
            category_path="Pets > Pet Accessories > Bowls & Feeders",
        )
    ]
    secondary = [
        InferredCategoryCandidate(
            l1="Pets",
            l2="Pet Healthcare",
            l3="Medication",
            category_path="Pets > Pet Healthcare > Medication",
        )
    ]
    merged = merge_candidates(primary, secondary)
    assert merged[0].category_path == "Pets > Pet Accessories > Bowls & Feeders"
    assert len(merged) == 2


def test_derive_single_category_when_one_above_threshold() -> None:
    candidates = propose_category_candidates(
        request_text="Bowls & Feeders market",
        category_text="Bowls & Feeders",
        top_k=3,
    )
    positioning = derive_positioning_type(candidates)
    assert positioning in {"single_category", "multi_category", "unresolved"}
