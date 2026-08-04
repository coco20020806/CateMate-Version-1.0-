from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_modules.daily_cncb_performance import ComputeParams, ScopedFrame, compute


def test_gmv_by_site_month() -> None:
    data = pd.DataFrame(
        {
            "grass_region": ["SG", "SG", "MY"],
            "month": ["2025-01-01", "2025-01-01", "2025-01-01"],
            "marketplace_gmv_usd(SUM)": [100, 200, 50],
            "cncb_gmv_usd(SUM)": [10, 20, 5],
            "marketplace_order(SUM)": [1, 2, 1],
            "cncb_order(SUM)": [1, 1, 0],
        }
    )
    frame = ScopedFrame(data=data, scope_label="test", scope_spec={})
    result = compute(ComputeParams(metric_id="gmv"), frame)["gmv_by_site_month"]

    sg = result[result["grass_region"] == "SG"].iloc[0]
    assert sg["marketplace_gmv_usd(SUM)"] == 300
    assert sg["cncb_gmv_usd(SUM)"] == 30
    assert result.attrs["metric_id"] == "gmv"


def test_orders_by_site_month() -> None:
    data = pd.DataFrame(
        {
            "grass_region": ["SG"],
            "grass_date": ["2025-02-10"],
            "marketplace_order(SUM)": [3],
            "cncb_order(SUM)": [2],
            "marketplace_gmv_usd(SUM)": [0],
            "cncb_gmv_usd(SUM)": [0],
        }
    )
    frame = ScopedFrame(data=data, scope_label="test", scope_spec={})
    result = compute(ComputeParams(metric_id="orders"), frame)["orders_by_site_month"]

    assert len(result) == 1
    assert result.iloc[0]["marketplace_order(SUM)"] == 3
    assert result.iloc[0]["cncb_order(SUM)"] == 2


def test_rejects_missing_gmv_columns() -> None:
    frame = ScopedFrame(
        data=pd.DataFrame(
            {"grass_region": ["SG"], "month": ["2025-01-01"], "marketplace_order(SUM)": [1]}
        ),
        scope_label="test",
        scope_spec={},
    )
    with pytest.raises(ValueError, match="marketplace_gmv_usd"):
        compute(ComputeParams(metric_id="gmv"), frame)
