"""Tests for subset vs parent comparison compute."""

from __future__ import annotations

import pandas as pd

from catemate.orchestration.comparison_compute import compute_subset_l3_share


def test_compute_subset_l3_share_ratio() -> None:
    subset = pd.DataFrame(
        {
            "grass_region": ["VN", "VN"],
            "grass_month": ["2026-01-01", "2026-02-01"],
            "gmv_usd": [100.0, 200.0],
        }
    )
    parent = pd.DataFrame(
        {
            "grass_region": ["VN", "VN"],
            "grass_month": ["2026-01-01", "2026-02-01"],
            "gmv_usd": [1000.0, 400.0],
        }
    )
    share = compute_subset_l3_share(subset_primary=subset, parent_primary=parent, metric_id="gmv")
    assert share.loc[0, "gmv_usd_share_of_l3"] == 0.1
    assert share.loc[1, "gmv_usd_share_of_l3"] == 0.5
