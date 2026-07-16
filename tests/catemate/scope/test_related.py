"""Tests for if_related concept pack filtering."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.scope.related import apply_if_related

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
    scope_note="宽定义：含智能饮水器/自动喂食器",
    smart_signals=[
        "smart",
        "automatic",
        "auto",
        "electric",
        "wireless",
        "sensor",
        "fountain",
        "dispenser",
        "feeder",
        "智能",
        "自动",
    ],
    pet_context=["pet", "cat", "dog", "猫", "狗"],
    boost_terms=["fountain", "dispenser", "feeder", "filter", "circulat"],
    exclude_terms=[
        "chicken",
        "poultry",
        "quail",
        "bird",
        "slow feed",
        "maze",
        "anti.?gulping",
        "replacement",
    ],
    min_score=0.55,
)

WIRELESS = (
    "Wireless Pet Water Fountain with Smart Sensor and Filter for Cat and Dog "
    "3.5L Stainless Steel"
)
DODO = (
    "DODO 3.2L Cat Fountain Drinking Cat Water Dispenser All Stainless Steel "
    "Automatic Circulating Filter Large Capacity"
)
CHICKEN = (
    "Automatic Chicken Waterer Drinker Bowl for Poultry Quail Pigeon Bird Rabbit "
    "quantity 40pcs"
)
SLOW_FEEDER = "Slow Feeder Bowl Maze Design for Dogs Anti-Gulping"
PLAIN_BOWL = "Stainless Steel Dog Bowl 500ml Non-Slip"


@pytest.fixture
def sample_df() -> pd.DataFrame:
    base = pd.read_csv(FIXTURE)
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
                "item_name": SLOW_FEEDER,
                "item_link": "http://example/slow",
                "shop_id": "1",
            },
            {
                "grass_month": "2026-06-01",
                "grass_region": "PH",
                "cb_level1_global_be_category": "Pets",
                "level2_global_be_category": "Pet Accessories",
                "level3_global_be_category": "Bowls & Feeders",
                "orders": 3.0,
                "gmv_usd": 12.0,
                "item_price_usd": 8.0,
                "price_range": "Tier4",
                "item_name": PLAIN_BOWL,
                "item_link": "http://example/plain",
                "shop_id": "2",
            },
        ]
    )
    return pd.concat([base, extra], ignore_index=True)


def test_related_keeps_smart_fountain_and_dispenser(sample_df: pd.DataFrame) -> None:
    result = apply_if_related(sample_df, SMART_PET_BOWL_PACK)
    names = set(result["item_name"])
    assert WIRELESS in names
    assert DODO in names


def test_related_excludes_chicken_and_slow_feeder(sample_df: pd.DataFrame) -> None:
    result = apply_if_related(sample_df, SMART_PET_BOWL_PACK)
    names = set(result["item_name"])
    assert CHICKEN not in names
    assert SLOW_FEEDER not in names
    assert PLAIN_BOWL not in names


def test_related_adds_diagnostic_columns(sample_df: pd.DataFrame) -> None:
    result = apply_if_related(sample_df, SMART_PET_BOWL_PACK)
    assert "related_score" in result.columns
    assert "related_matched_terms" in result.columns
    assert "is_related" in result.columns
    assert all(result["is_related"])


def test_related_dedup_scores_by_item_name() -> None:
    df = pd.DataFrame(
        {
            "item_name": [WIRELESS, WIRELESS, DODO],
            "orders": [1.0, 2.0, 3.0],
        }
    )
    result = apply_if_related(df, SMART_PET_BOWL_PACK)
    assert len(result) == 3
    assert result.loc[result["item_name"] == WIRELESS, "related_score"].nunique() == 1


def test_related_skips_when_no_item_name_column() -> None:
    df = pd.DataFrame({"orders": [1.0, 2.0]})
    result = apply_if_related(df, SMART_PET_BOWL_PACK)
    assert len(result) == 2


def test_related_empty_dataframe() -> None:
    result = apply_if_related(pd.DataFrame(), SMART_PET_BOWL_PACK)
    assert result.empty
