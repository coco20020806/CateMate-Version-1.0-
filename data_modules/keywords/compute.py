"""keywords — top keywords by daily item clicks."""

from __future__ import annotations

import pandas as pd

from catemate.scope.schemas import ScopedFrame

COL_KEYWORD = "keyword"
COL_CLICKS = "current_daily_item_click(SUM)"

TABLE_ID = "top_keywords"
GROUP_BY = (COL_KEYWORD,)
TOP_N = 20
SORT_BY = COL_CLICKS


def _validate_required_columns(frame: ScopedFrame) -> None:
    missing = [c for c in (*GROUP_BY, COL_CLICKS) if c not in frame.data.columns]
    if missing:
        raise ValueError(
            f"Missing required columns {missing}; see source_schema.yaml → source_columns"
        )


def compute(frame: ScopedFrame) -> dict[str, pd.DataFrame]:
    _validate_required_columns(frame)

    grouped = (
        frame.data.groupby(list(GROUP_BY), dropna=False, as_index=False)
        .agg({COL_CLICKS: "sum"})
    )
    result = (
        grouped.sort_values(SORT_BY, ascending=False, na_position="last")
        .head(TOP_N)
        .reset_index(drop=True)
    )

    result.attrs["scope_label"] = frame.scope_label
    result.attrs["scope_spec"] = frame.scope_spec
    result.attrs["source_id"] = frame.source_id
    result.attrs["module_id"] = "keywords"
    result.attrs["top_n"] = TOP_N

    return {TABLE_ID: result}
