"""Tests for ScopeCache."""

from __future__ import annotations

import pandas as pd

from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.scope.scope_cache import ScopeCache, cache_key
from catemate.scope.schemas import ScopedFrame, ScopeSpec


def _pack() -> RelatedConceptPack:
    return RelatedConceptPack(
        concept_id="smart_pet_feeder",
        display_name="智能喂食器",
        parent_l3="Bowls & Feeders",
        scope_note="test",
        smart_signals=["smart", "feeder"],
        pet_context=["pet"],
        boost_terms=["feeder"],
        exclude_terms=["chicken"],
        min_score=0.55,
    )


def _spec() -> ScopeSpec:
    return ScopeSpec(
        grain="item",
        table_id="item_l3_category_csv",
        category_l1="Pets",
        category_l2="Pet Accessories",
        category_l3="Bowls & Feeders",
        related_concept_pack=_pack(),
        related_min_score=0.55,
    )


def test_cache_key_ignores_scope_label() -> None:
    left = _spec()
    right = _spec()
    right.scope_label = "different label"
    assert cache_key(left) == cache_key(right)


def test_cache_get_put_roundtrip() -> None:
    cache = ScopeCache()
    spec = _spec()
    frame = ScopedFrame(
        data=pd.DataFrame({"item_name": ["smart feeder"], "orders": [1]}),
        scope_label="test",
        scope_spec={},
    )
    cache.put(spec, frame, input_rows=10)
    loaded = cache.get(spec)
    assert loaded is not None
    assert len(loaded.data) == 1
    assert cache.entries[cache_key(spec)]["input_rows"] == 10


def test_cache_save_and_load_from_dir(tmp_path) -> None:
    cache = ScopeCache()
    spec = _spec()
    frame = ScopedFrame(
        data=pd.DataFrame({"item_name": ["smart feeder"], "orders": [1]}),
        scope_label="test",
        scope_spec={},
    )
    cache.put(spec, frame, input_rows=5)
    cache.save_to_dir(tmp_path)

    reloaded = ScopeCache.load_from_dir(tmp_path)
    assert reloaded is not None
    loaded = reloaded.get(spec)
    assert loaded is not None
    assert len(loaded.data) == 1
