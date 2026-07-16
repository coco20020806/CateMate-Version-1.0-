"""top_sku_info — Top N SKU listings by orders or GMV per site×month."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

from catemate.scope.schemas import ScopedFrame

COL_SITE = "grass_region"
COL_MONTH = "grass_month"
COL_DATE = "grass_date"
COL_ITEM = "item_name"
COL_LINK = "item_link"
COL_ORDERS = "orders"
COL_GMV = "gmv_usd"

TIME_COLUMNS = (COL_MONTH, COL_DATE)
METRIC_COLUMNS = (COL_ORDERS, COL_GMV)

REQUIRED_COLUMNS = (COL_SITE, COL_ITEM, COL_LINK)
GROUP_BY = (COL_SITE, COL_MONTH, COL_ITEM)
SLICE_BY = (COL_SITE, COL_MONTH)

SOFT_EXPECTED_COLUMNS = (
    "item_price_usd",
    "price_range",
    "cb_level1_global_be_category",
    "level2_global_be_category",
    "level3_global_be_category",
    "shop_id",
    "item_image",
)

SortBy = Literal["orders", "gmv", "both"]
SortMetricId = Literal["orders", "gmv"]

SORT_METRIC_SOURCE: dict[SortMetricId, str] = {
    "orders": COL_ORDERS,
    "gmv": COL_GMV,
}

DEFAULT_TOP_N = (5, 10, 20)

BASE_OUTPUT_COLUMNS = (COL_SITE, COL_MONTH, "rank", COL_ITEM, COL_LINK)


@dataclass(frozen=True)
class ComputeParams:
    top_n: int | None = None
    sort_by: SortBy = "both"


def table_id(sort_metric: SortMetricId, top_n: int) -> str:
    return f"top_sku_by_{sort_metric}_top{top_n}"


def _validate_required_columns(frame: ScopedFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.data.columns]
    if missing:
        raise ValueError(
            f"Missing required columns {missing}; see source_schema.yaml → source_columns"
        )
    if not any(col in frame.data.columns for col in TIME_COLUMNS):
        raise ValueError(f"Missing time column; need one of {TIME_COLUMNS}")
    if not any(col in frame.data.columns for col in METRIC_COLUMNS):
        raise ValueError(
            f"Missing sort metric column; need at least one of {METRIC_COLUMNS}"
        )


def _normalize_month_column(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if COL_MONTH in result.columns:
        result[COL_MONTH] = result[COL_MONTH].astype(str)
        return result

    if COL_DATE not in result.columns:
        raise ValueError(f"Need {COL_MONTH} or {COL_DATE} for time aggregation")

    parsed = pd.to_datetime(result[COL_DATE], errors="coerce")
    result[COL_MONTH] = (
        parsed.dt.to_period("M").dt.to_timestamp().dt.strftime("%Y-%m-%d")
    )
    return result


def _input_quality_flags(
    df: pd.DataFrame,
    *,
    sort_by_requested: str,
    sort_by_effective: list[str],
    sort_by_degraded: bool,
    top_n_values: list[int],
) -> dict[str, Any]:
    missing_soft = [c for c in SOFT_EXPECTED_COLUMNS if c not in df.columns]
    return {
        "sort_by_requested": sort_by_requested,
        "sort_by_effective": sort_by_effective,
        "sort_by_degraded": sort_by_degraded,
        "top_n_values": top_n_values,
        "missing_soft_expected": missing_soft,
    }


def _resolve_sort_metrics(
    sort_by: SortBy, columns: pd.Index
) -> tuple[list[SortMetricId], bool]:
    has_orders = COL_ORDERS in columns
    has_gmv = COL_GMV in columns

    if sort_by == "orders":
        if not has_orders:
            raise ValueError(f"sort_by=orders requires column {COL_ORDERS}")
        return ["orders"], False
    if sort_by == "gmv":
        if not has_gmv:
            raise ValueError(f"sort_by=gmv requires column {COL_GMV}")
        return ["gmv"], False

    if has_orders and has_gmv:
        return ["orders", "gmv"], False
    if has_orders:
        return ["orders"], True
    if has_gmv:
        return ["gmv"], True
    raise ValueError(f"Need at least one of {METRIC_COLUMNS}")


def _resolve_top_n_values(top_n: int | None) -> list[int]:
    if top_n is None:
        return list(DEFAULT_TOP_N)
    if top_n <= 0:
        raise ValueError(f"top_n must be positive; got {top_n}")
    return [top_n]


def _aggregate_items(working: pd.DataFrame) -> pd.DataFrame:
    present_metrics = [c for c in METRIC_COLUMNS if c in working.columns]
    first_cols = [
        c
        for c in (*SOFT_EXPECTED_COLUMNS, COL_LINK)
        if c in working.columns and c not in present_metrics
    ]

    agg: dict[str, str] = {c: "sum" for c in present_metrics}
    agg.update({c: "first" for c in first_cols})

    return (
        working.groupby(list(GROUP_BY), dropna=False, as_index=False)
        .agg(agg)
    )


def _output_columns(aggregated: pd.DataFrame) -> list[str]:
    cols = list(BASE_OUTPUT_COLUMNS)
    for col in METRIC_COLUMNS:
        if col in aggregated.columns and col not in cols:
            cols.append(col)
    for col in SOFT_EXPECTED_COLUMNS:
        if col in aggregated.columns and col not in cols:
            cols.append(col)
    return cols


def _rank_top_n(
    slice_df: pd.DataFrame,
    *,
    sort_metric: SortMetricId,
    top_n: int,
    output_columns: list[str],
) -> pd.DataFrame:
    sort_col = SORT_METRIC_SOURCE[sort_metric]
    if slice_df.empty:
        return pd.DataFrame(columns=output_columns)

    ordered = slice_df.sort_values(sort_col, ascending=False, na_position="last")
    ordered = ordered.copy()
    ordered["rank"] = (
        ordered[sort_col].rank(method="min", ascending=False).astype("Int64")
    )
    result = ordered.head(top_n)
    return result[output_columns].reset_index(drop=True)


def _build_ranking_table(
    aggregated: pd.DataFrame,
    *,
    sort_metric: SortMetricId,
    top_n: int,
    output_columns: list[str],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for _, slice_df in aggregated.groupby(list(SLICE_BY), sort=False):
        frames.append(
            _rank_top_n(
                slice_df,
                sort_metric=sort_metric,
                top_n=top_n,
                output_columns=output_columns,
            )
        )

    if not frames:
        return pd.DataFrame(columns=output_columns)

    result = pd.concat(frames, ignore_index=True)
    return result.sort_values([COL_SITE, COL_MONTH, "rank"]).reset_index(drop=True)


def compute(params: ComputeParams, frame: ScopedFrame) -> dict[str, pd.DataFrame]:
    _validate_required_columns(frame)

    working = _normalize_month_column(frame.data)
    sort_metrics, sort_by_degraded = _resolve_sort_metrics(
        params.sort_by, working.columns
    )
    top_n_values = _resolve_top_n_values(params.top_n)

    aggregated = _aggregate_items(working)
    output_columns = _output_columns(aggregated)

    input_quality = _input_quality_flags(
        working,
        sort_by_requested=params.sort_by,
        sort_by_effective=list(sort_metrics),
        sort_by_degraded=sort_by_degraded,
        top_n_values=top_n_values,
    )

    results: dict[str, pd.DataFrame] = {}
    for sort_metric in sort_metrics:
        for n in top_n_values:
            table = _build_ranking_table(
                aggregated,
                sort_metric=sort_metric,
                top_n=n,
                output_columns=output_columns,
            )
            table.attrs["scope_label"] = frame.scope_label
            table.attrs["scope_spec"] = frame.scope_spec
            table.attrs["source_id"] = frame.source_id
            table.attrs["module_id"] = "top_sku_info"
            table.attrs["sort_metric"] = sort_metric
            table.attrs["top_n"] = n
            table.attrs["input_quality"] = input_quality
            results[table_id(sort_metric, n)] = table

    return results
