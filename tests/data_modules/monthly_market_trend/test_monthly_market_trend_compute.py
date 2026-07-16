from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_modules.monthly_market_trend import ComputeParams, ScopedFrame, compute, transform

FIXTURES = ROOT / "tests" / "fixtures" / "data_modules" / "monthly_market_trend"


@pytest.fixture
def scoped_frame() -> ScopedFrame:
    data = pd.read_csv(FIXTURES / "sample_scoped.csv")
    return ScopedFrame(
        data=data,
        scope_label="ALL / Stationery > Notebooks / L2 / 2025-01~02",
        scope_spec={},
        source_id="external_scope",
    )


def test_gmv_primary_table(scoped_frame: ScopedFrame) -> None:
    primary = compute(ComputeParams(metric_id="gmv"), scoped_frame)["gmv_by_site_month"]
    assert list(primary.columns) == ["grass_region", "grass_month", "gmv_usd"]
    assert primary.attrs["metric_id"] == "gmv"
    sg_feb = primary[
        (primary["grass_region"] == "SG") & (primary["grass_month"] == "2025-02-01")
    ].iloc[0]
    assert sg_feb["gmv_usd"] == 2500


def test_orders_primary_table(scoped_frame: ScopedFrame) -> None:
    primary = compute(ComputeParams(metric_id="orders"), scoped_frame)[
        "orders_by_site_month"
    ]
    sg_feb = primary[
        (primary["grass_region"] == "SG") & (primary["grass_month"] == "2025-02-01")
    ].iloc[0]
    assert sg_feb["orders"] == 5


def test_aov_primary_table(scoped_frame: ScopedFrame) -> None:
    primary = compute(ComputeParams(metric_id="aov"), scoped_frame)["aov_by_site_month"]
    sg_feb = primary[
        (primary["grass_region"] == "SG") & (primary["grass_month"] == "2025-02-01")
    ].iloc[0]
    assert sg_feb["aov"] == 500


def test_gmv_derived_three_tables(scoped_frame: ScopedFrame) -> None:
    derived = transform(compute(ComputeParams(metric_id="gmv"), scoped_frame))

    latest = derived["gmv_latest_month_by_site"]
    assert len(latest) == 2
    assert sorted(latest["gmv_usd"].tolist()) == [1200.0, 2500.0]

    pct = derived["gmv_latest_month_pct_by_site"]
    assert pytest.approx(pct["gmv_usd_pct"].sum(), rel=1e-6) == 1.0

    mom = derived["gmv_mom_by_site_month"]
    sg_mom = mom[mom["grass_region"] == "SG"].sort_values("grass_month")
    assert pd.isna(sg_mom.iloc[0]["gmv_usd_mom_pct"])
    assert sg_mom.iloc[1]["gmv_usd_mom_pct"] == pytest.approx(1.5)


def test_orders_derived_mom(scoped_frame: ScopedFrame) -> None:
    mom = transform(compute(ComputeParams(metric_id="orders"), scoped_frame))[
        "orders_mom_by_site_month"
    ]
    sg = mom[mom["grass_region"] == "SG"].sort_values("grass_month").iloc[1]
    assert sg["orders_mom_pct"] == pytest.approx(-0.5)


def test_grass_date_with_gmv_metric() -> None:
    data = pd.DataFrame(
        {
            "grass_region": ["SG", "SG"],
            "grass_date": ["2025-02-10", "2025-02-20"],
            "gmv_usd": [100, 200],
        }
    )
    frame = ScopedFrame(data=data, scope_label="date-only", scope_spec={})
    primary = compute(ComputeParams(metric_id="gmv"), frame)["gmv_by_site_month"]
    assert len(primary) == 1
    assert primary.iloc[0]["gmv_usd"] == 300


def test_gmv_rejects_missing_source_column() -> None:
    frame = ScopedFrame(
        data=pd.DataFrame(
            {"grass_region": ["SG"], "grass_month": ["2025-01-01"], "orders": [1]}
        ),
        scope_label="no-gmv",
        scope_spec={},
    )
    with pytest.raises(ValueError, match="gmv_usd"):
        compute(ComputeParams(metric_id="gmv"), frame)


def test_aov_requires_both_source_columns() -> None:
    frame = ScopedFrame(
        data=pd.DataFrame(
            {"grass_region": ["SG"], "grass_month": ["2025-01-01"], "gmv_usd": [100]}
        ),
        scope_label="no-orders",
        scope_spec={},
    )
    with pytest.raises(ValueError, match="orders"):
        compute(ComputeParams(metric_id="aov"), frame)


def test_missing_category_not_blocking() -> None:
    data = pd.DataFrame(
        {
            "grass_region": ["SG"],
            "grass_month": ["2025-01-01"],
            "gmv_usd": [100],
        }
    )
    frame = ScopedFrame(data=data, scope_label="no-category", scope_spec={})
    primary = compute(ComputeParams(metric_id="gmv"), frame)["gmv_by_site_month"]
    assert primary.attrs["input_quality"]["has_all_category_columns"] is False
