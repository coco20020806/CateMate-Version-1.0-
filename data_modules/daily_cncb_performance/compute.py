"""daily_cncb_performance — Shopee/CNCB GMV or orders by site×month."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

from catemate.scope.schemas import ScopedFrame

COL_SITE = "grass_region"
COL_MONTH = "month"
COL_GRASS_MONTH = "grass_month"
COL_DATE = "grass_date"

COL_SHOPEE_GMV = "shopee_gmv_usd(SUM)"
COL_SHOPEE_ORDER = "shopee_order(SUM)"
COL_CNCB_GMV = "cncb_gmv_usd(SUM)"
COL_CNCB_ORDER = "cncb_order(SUM)"

TIME_COLUMNS = (COL_MONTH, COL_GRASS_MONTH, COL_DATE)

MetricId = Literal["gmv", "orders"]

METRIC_SPECS: dict[str, dict[str, Any]] = {
    "gmv": {
        "table_id": "gmv_by_site_month",
        "value_columns": (COL_SHOPEE_GMV, COL_CNCB_GMV),
    },
    "orders": {
        "table_id": "orders_by_site_month",
        "value_columns": (COL_SHOPEE_ORDER, COL_CNCB_ORDER),
    },
}

GROUP_BY = (COL_SITE, COL_MONTH)


@dataclass(frozen=True)
class ComputeParams:
    metric_id: MetricId = "gmv"


def _validate_required_columns(frame: ScopedFrame, metric_id: str) -> None:
    if COL_SITE not in frame.data.columns:
        raise ValueError(f"Missing required column {COL_SITE}")
    if not any(col in frame.data.columns for col in TIME_COLUMNS):
        raise ValueError(f"Missing time column; need one of {TIME_COLUMNS}")

    spec = METRIC_SPECS[metric_id]
    missing = [c for c in spec["value_columns"] if c not in frame.data.columns]
    if missing:
        raise ValueError(
            f"metric_id={metric_id} requires source columns {missing}; "
            f"see source_schema.yaml → compute_rules.metrics"
        )


def _normalize_month_column(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if COL_MONTH in result.columns:
        result[COL_MONTH] = result[COL_MONTH].astype(str)
        return result

    if COL_GRASS_MONTH in result.columns:
        result[COL_MONTH] = result[COL_GRASS_MONTH].astype(str)
        return result

    if COL_DATE not in result.columns:
        raise ValueError(f"Need {COL_MONTH}, {COL_GRASS_MONTH}, or {COL_DATE} for time aggregation")

    parsed = pd.to_datetime(result[COL_DATE], errors="coerce")
    result[COL_MONTH] = (
        parsed.dt.to_period("M").dt.to_timestamp().dt.strftime("%Y-%m-%d")
    )
    return result


def _aggregate_metric(working: pd.DataFrame, metric_id: str) -> pd.DataFrame:
    spec = METRIC_SPECS[metric_id]
    value_cols: tuple[str, ...] = spec["value_columns"]
    grouped = (
        working.groupby(list(GROUP_BY), dropna=False, as_index=False)
        .agg({col: "sum" for col in value_cols})
    )
    return grouped


def compute(params: ComputeParams, frame: ScopedFrame) -> dict[str, pd.DataFrame]:
    metric_id = params.metric_id
    if metric_id not in METRIC_SPECS:
        raise ValueError(f"Unknown metric_id={metric_id}; expected gmv|orders")

    _validate_required_columns(frame, metric_id)

    working = _normalize_month_column(frame.data)
    result = _aggregate_metric(working, metric_id)
    result = result.sort_values([COL_SITE, COL_MONTH]).reset_index(drop=True)

    table_id = METRIC_SPECS[metric_id]["table_id"]
    result.attrs["scope_label"] = frame.scope_label
    result.attrs["scope_spec"] = frame.scope_spec
    result.attrs["source_id"] = frame.source_id
    result.attrs["module_id"] = "daily_cncb_performance"
    result.attrs["metric_id"] = metric_id

    return {table_id: result}
