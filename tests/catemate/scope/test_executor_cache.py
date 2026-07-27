"""Tests for execute_scope cache integration."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.scope.executor import execute_scope
from catemate.scope.scope_cache import ScopeCache
from catemate.scope.schemas import ScopedFrame, ScopeSpec


def _spec() -> ScopeSpec:
    return ScopeSpec(
        grain="item",
        table_id="item_l3_category_csv",
        category_l1="Pets",
        category_l2="Pet Accessories",
        category_l3="Bowls & Feeders",
        related_concept_pack=RelatedConceptPack(
            concept_id="smart_pet_feeder",
            display_name="智能喂食器",
            parent_l3="Bowls & Feeders",
            scope_note="test",
            smart_signals=["smart"],
            pet_context=["pet"],
            boost_terms=["feeder"],
            exclude_terms=["chicken"],
            min_score=0.55,
        ),
    )


def test_execute_scope_uses_cache_without_reload() -> None:
    cache = ScopeCache()
    spec = _spec()
    cached = pd.DataFrame({"item_name": ["smart feeder"], "orders": [1]})
    cache.put(
        spec,
        ScopedFrame(data=cached.copy(), scope_label="cached", scope_spec={}),
    )

    with patch("catemate.scope.executor.load_table_for_scope") as mock_load:
        with patch("catemate.scope.executor.apply_if_related") as mock_related:
            frame = execute_scope(spec, scope_cache=cache)
            mock_load.assert_not_called()
            mock_related.assert_not_called()
            assert len(frame.data) == 1
