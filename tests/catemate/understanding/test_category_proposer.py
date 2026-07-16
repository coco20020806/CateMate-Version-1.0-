"""Tests for category proposer."""

from __future__ import annotations

from catemate.understanding.category_proposer import (
    derive_positioning_type,
    propose_category_candidates,
)


def test_propose_returns_candidates_for_pet_bowl_request() -> None:
    candidates = propose_category_candidates(
        request_text="分析菲律宾站智能宠物碗",
        category_text="智能宠物碗",
    )
    assert candidates
    paths = [c.category_path for c in candidates]
    assert any("Bowls" in path or "Feeder" in path or "Pet" in path for path in paths)


def test_derive_single_category_when_one_above_threshold() -> None:
    candidates = propose_category_candidates(
        request_text="Bowls & Feeders market",
        category_text="Bowls & Feeders",
        top_k=3,
    )
    positioning = derive_positioning_type(candidates)
    assert positioning in {"single_category", "multi_category", "unresolved"}
