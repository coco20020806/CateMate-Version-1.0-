"""Tests for category_tree_en.json loading and category mapping."""

from __future__ import annotations

from catemate.data.category_tree_en import flatten_category_tree, list_category_tree_candidates
from catemate.understanding.category_mapper import resolve_category_mapping


def test_category_tree_has_pets_paths() -> None:
    paths = flatten_category_tree()
    assert any(item.l1 == "Pets" and item.l3 == "Dog Food" for item in paths)
    candidates = list_category_tree_candidates()
    assert any(item["category_path"] == "Pets > Pet Food > Dog Food" for item in candidates)


def test_map_dog_food_to_l3() -> None:
    result = resolve_category_mapping(request_text="分析 VN 狗粮月度 GMV 趋势", category_text="狗粮")
    assert result.is_relevant
    assert result.mapped_level == "L3"
    assert result.category_path == "Pets > Pet Food > Dog Food"


def test_map_pet_staple_food_to_l2() -> None:
    result = resolve_category_mapping(request_text="VN 宠物主粮月度趋势", category_text="宠物主粮")
    assert result.is_relevant
    assert result.mapped_level == "L2"
    assert result.category_path == "Pets > Pet Food"


def test_map_pet_category_to_l1() -> None:
    result = resolve_category_mapping(
        request_text="VN 宠物类目月度 GMV 趋势 + 头部 shop 对比",
        category_text="宠物类目",
    )
    assert result.is_relevant
    assert result.mapped_level == "L1"
    assert result.l1 == "Pets"


def test_irrelevant_input() -> None:
    result = resolve_category_mapping(request_text="今天天气怎么样", category_text="")
    assert not result.is_relevant
