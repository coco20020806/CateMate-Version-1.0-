"""price_tier_distribution — ADO/ADG by price tier and site."""

from __future__ import annotations

import pandas as pd

from catemate.scope.schemas import ScopedFrame

COL_SITE = "grass_region"
COL_PRICE_TIER = "Price_Range_USD"
COL_ADO = "ADO"
COL_ADG = "ADG"

TABLE_ID = "price_tier_by_site"
GROUP_BY = (COL_PRICE_TIER, COL_SITE)
VALUE_COLUMNS = (COL_ADO, COL_ADG)


def _validate_required_columns(frame: ScopedFrame) -> None:
    missing = [c for c in (*GROUP_BY, *VALUE_COLUMNS) if c not in frame.data.columns]
    if missing:
        raise ValueError(
            f"Missing required columns {missing}; see source_schema.yaml → source_columns"
        )


def compute(frame: ScopedFrame) -> dict[str, pd.DataFrame]:
    _validate_required_columns(frame)

    result = (
        frame.data.groupby(list(GROUP_BY), dropna=False, as_index=False)
        .agg({col: "sum" for col in VALUE_COLUMNS})
        .sort_values([COL_SITE, COL_PRICE_TIER])
        .reset_index(drop=True)
    )

    result.attrs["scope_label"] = frame.scope_label
    result.attrs["scope_spec"] = frame.scope_spec
    result.attrs["source_id"] = frame.source_id
    result.attrs["module_id"] = "price_tier_distribution"

    return {TABLE_ID: result}
