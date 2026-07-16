"""top_listing — top listings by ADGMV and ADO."""

from __future__ import annotations

import pandas as pd

from catemate.scope.schemas import ScopedFrame

COL_ITEM = "item_name"
COL_ADGMV = "current_adgmv(RAW)"
COL_ADO = "current_ado(RAW)"

TABLE_ID = "top_listing_ranking"
GROUP_BY = (COL_ITEM,)
VALUE_COLUMNS = (COL_ADGMV, COL_ADO)
TOP_N = 20
SORT_BY = COL_ADGMV


def _validate_required_columns(frame: ScopedFrame) -> None:
    missing = [c for c in (*GROUP_BY, *VALUE_COLUMNS) if c not in frame.data.columns]
    if missing:
        raise ValueError(
            f"Missing required columns {missing}; see source_schema.yaml → source_columns"
        )


def compute(frame: ScopedFrame) -> dict[str, pd.DataFrame]:
    _validate_required_columns(frame)

    grouped = (
        frame.data.groupby(list(GROUP_BY), dropna=False, as_index=False)
        .agg({col: "sum" for col in VALUE_COLUMNS})
    )
    result = (
        grouped.sort_values(SORT_BY, ascending=False, na_position="last")
        .head(TOP_N)
        .reset_index(drop=True)
    )

    result.attrs["scope_label"] = frame.scope_label
    result.attrs["scope_spec"] = frame.scope_spec
    result.attrs["source_id"] = frame.source_id
    result.attrs["module_id"] = "top_listing"
    result.attrs["top_n"] = TOP_N

    return {TABLE_ID: result}
