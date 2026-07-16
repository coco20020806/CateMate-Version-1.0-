from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_modules.top_sku_info import ComputeParams, ScopedFrame, compute

FIXTURES = ROOT / "tests" / "fixtures" / "data_modules" / "top_sku_info"

WIRELESS = (
    "Wireless Pet Water Fountain with Smart Sensor and Filter "
    "for Cat and Dog 3.5L Stainless Steel"
)
DODO = (
    "DODO 3.2L Cat Fountain Drinking Cat Water Dispenser All Stainless Steel "
    "Automatic Circulating Filter Large Capacity"
)


@pytest.fixture
def scoped_frame() -> ScopedFrame:
    data = pd.read_csv(FIXTURES / "sample_scoped.csv")
    return ScopedFrame(
        data=data,
        scope_label="PH / Pets > Pet Accessories > Bowls & Feeders / 2026-06",
        scope_spec={},
        source_id="item_l3_category_csv",
    )


def test_orders_top2(scoped_frame: ScopedFrame) -> None:
    result = compute(ComputeParams(top_n=2, sort_by="orders"), scoped_frame)
    table = result["top_sku_by_orders_top2"]

    assert len(table) == 2
    assert table.iloc[0]["rank"] == 1
    assert table.iloc[0]["item_name"] == WIRELESS
    assert table.iloc[0]["orders"] == 18.0
    assert table.iloc[1]["rank"] == 2
    assert table.iloc[1]["item_name"] == DODO
    assert table.iloc[1]["orders"] == 2.0


def test_gmv_top2(scoped_frame: ScopedFrame) -> None:
    result = compute(ComputeParams(top_n=2, sort_by="gmv"), scoped_frame)
    table = result["top_sku_by_gmv_top2"]

    assert len(table) == 2
    assert table.iloc[0]["item_name"] == WIRELESS
    assert table.iloc[0]["gmv_usd"] == pytest.approx(345.06670564239994)
    assert table.iloc[1]["item_name"] == DODO
    assert table.iloc[1]["gmv_usd"] == pytest.approx(78.7475741558)


def test_default_produces_six_tables(scoped_frame: ScopedFrame) -> None:
    result = compute(ComputeParams(), scoped_frame)
    assert set(result.keys()) == {
        "top_sku_by_orders_top5",
        "top_sku_by_orders_top10",
        "top_sku_by_orders_top20",
        "top_sku_by_gmv_top5",
        "top_sku_by_gmv_top10",
        "top_sku_by_gmv_top20",
    }


def test_sort_by_both_degrades_when_orders_only(scoped_frame: ScopedFrame) -> None:
    data = scoped_frame.data.drop(columns=["gmv_usd"])
    frame = ScopedFrame(
        data=data,
        scope_label=scoped_frame.scope_label,
        scope_spec={},
        source_id="item_l3_category_csv",
    )
    result = compute(ComputeParams(top_n=5), frame)

    assert set(result.keys()) == {"top_sku_by_orders_top5"}
    quality = result["top_sku_by_orders_top5"].attrs["input_quality"]
    assert quality["sort_by_degraded"] is True
    assert quality["sort_by_effective"] == ["orders"]


def test_missing_item_image_not_blocking(scoped_frame: ScopedFrame) -> None:
    result = compute(ComputeParams(top_n=2, sort_by="orders"), scoped_frame)
    quality = result["top_sku_by_orders_top2"].attrs["input_quality"]
    assert "item_image" in quality["missing_soft_expected"]


def test_grass_date_normalization() -> None:
    data = pd.DataFrame(
        {
            "grass_region": ["PH", "PH"],
            "grass_date": ["2026-06-10", "2026-06-20"],
            "item_name": ["sku-a", "sku-b"],
            "item_link": ["http://a", "http://b"],
            "orders": [5.0, 10.0],
            "gmv_usd": [50.0, 20.0],
        }
    )
    frame = ScopedFrame(data=data, scope_label="date-only", scope_spec={})
    table = compute(ComputeParams(top_n=1, sort_by="orders"), frame)[
        "top_sku_by_orders_top1"
    ]

    assert len(table) == 1
    assert table.iloc[0]["grass_month"] == "2026-06-01"
    assert table.iloc[0]["item_name"] == "sku-b"


def test_rejects_missing_item_link() -> None:
    frame = ScopedFrame(
        data=pd.DataFrame(
            {
                "grass_region": ["PH"],
                "grass_month": ["2026-06-01"],
                "item_name": ["sku-a"],
                "orders": [1.0],
            }
        ),
        scope_label="no-link",
        scope_spec={},
    )
    with pytest.raises(ValueError, match="item_link"):
        compute(ComputeParams(top_n=1, sort_by="orders"), frame)
