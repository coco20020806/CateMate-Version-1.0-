"""End-to-end tests for Scope + if_related + top_sku_info."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.scope.related import apply_if_related
from catemate.scope.schemas import ScopedFrame
from data_modules.top_sku_info import ComputeParams, compute

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "data_modules"
    / "top_sku_info"
    / "sample_scoped.csv"
)

SMART_PET_BOWL_PACK = RelatedConceptPack(
    concept_id="smart_pet_bowl",
    display_name="智能宠物碗",
    parent_l3="Bowls & Feeders",
    smart_signals=["smart", "automatic", "fountain", "dispenser", "feeder"],
    pet_context=["pet", "cat", "dog"],
    boost_terms=["fountain", "dispenser", "feeder"],
    exclude_terms=["chicken", "poultry", "slow feed", "maze"],
    min_score=0.55,
)


@pytest.mark.integration
def test_scope_if_related_top_sku_info_pipeline() -> None:
    df = pd.read_csv(FIXTURE)
    extra = pd.DataFrame(
        [
            {
                "grass_month": "2026-06-01",
                "grass_region": "PH",
                "cb_level1_global_be_category": "Pets",
                "level2_global_be_category": "Pet Accessories",
                "level3_global_be_category": "Bowls & Feeders",
                "orders": 5.0,
                "gmv_usd": 20.0,
                "item_price_usd": 10.0,
                "price_range": "Tier5",
                "item_name": "Slow Feeder Bowl Maze Design for Dogs Anti-Gulping",
                "item_link": "http://example/slow",
                "shop_id": "1",
            }
        ]
    )
    combined = pd.concat([df, extra], ignore_index=True)

    from catemate.scope.filters import apply_scope_filters
    from catemate.scope.schemas import ScopeSpec

    spec = ScopeSpec(
        grain="item",
        table_id="fixture",
        target_sites=["PH"],
        related_concept_pack=SMART_PET_BOWL_PACK,
    )
    scoped = apply_scope_filters(combined, spec)
    related = apply_if_related(scoped, SMART_PET_BOWL_PACK)

    assert len(related) == 2
    frame = ScopedFrame(data=related, scope_label="PH / smart_pet_bowl")
    tables = compute(ComputeParams(top_n=2, sort_by="both"), frame)
    assert "top_sku_by_orders_top2" in tables
    assert tables["top_sku_by_orders_top2"].iloc[0]["item_name"].startswith("Demo")
