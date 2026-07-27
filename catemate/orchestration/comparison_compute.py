"""Pure subset vs parent L3 share table computation."""

from __future__ import annotations

import pandas as pd

from data_modules.monthly_market_trend.compute import COL_MONTH, COL_SITE, METRIC_SPECS

_VALUE_BY_METRIC = {
    metric_id: str(spec["value_column"])
    for metric_id, spec in METRIC_SPECS.items()
}


def compute_subset_l3_share(
    *,
    subset_primary: pd.DataFrame,
    parent_primary: pd.DataFrame,
    metric_id: str,
) -> pd.DataFrame:
    value_column = _VALUE_BY_METRIC[metric_id]
    share_column = f"{value_column}_share_of_l3"

    if subset_primary.empty or parent_primary.empty:
        return pd.DataFrame(
            columns=[COL_SITE, COL_MONTH, f"subset_{value_column}", f"parent_{value_column}", share_column]
        )

    subset = subset_primary[[COL_SITE, COL_MONTH, value_column]].rename(
        columns={value_column: f"subset_{value_column}"}
    )
    parent = parent_primary[[COL_SITE, COL_MONTH, value_column]].rename(
        columns={value_column: f"parent_{value_column}"}
    )
    merged = subset.merge(parent, on=[COL_SITE, COL_MONTH], how="outer")
    merged[share_column] = merged.apply(
        lambda row: (
            None
            if pd.isna(row[f"parent_{value_column}"])
            or row[f"parent_{value_column}"] == 0
            or pd.isna(row[f"subset_{value_column}"])
            else float(row[f"subset_{value_column}"]) / float(row[f"parent_{value_column}"])
        ),
        axis=1,
    )
    return merged.sort_values([COL_SITE, COL_MONTH]).reset_index(drop=True)
