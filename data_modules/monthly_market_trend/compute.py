"""monthly_market_trend — one metric → one primary site×month table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

from catemate.scope.schemas import ScopedFrame

COL_SITE = "grass_region"
COL_MONTH = "grass_month"
COL_DATE = "grass_date"
COL_GMV = "gmv_usd"
COL_ORDERS = "orders"
COL_AOV = "aov"

TIME_COLUMNS = (COL_MONTH, COL_DATE)
CATEGORY_COLUMNS = (
    "cb_level1_global_be_category",
    "level2_global_be_category",
    "level3_global_be_category",
)

MetricId = Literal["gmv", "orders", "aov"]

METRIC_SPECS: dict[str, dict[str, Any]] = {
    "gmv": {
        "table_id": "gmv_by_site_month",
        "value_column": COL_GMV,
        "required_source": (COL_GMV,),
    },
    "orders": {
        "table_id": "orders_by_site_month",
        "value_column": COL_ORDERS,
        "required_source": (COL_ORDERS,),
    },
    "aov": {
        "table_id": "aov_by_site_month",
        "value_column": COL_AOV,
        "required_source": (COL_GMV, COL_ORDERS),
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
    missing = [c for c in spec["required_source"] if c not in frame.data.columns]
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

    if COL_DATE not in result.columns:
        raise ValueError(f"Need {COL_MONTH} or {COL_DATE} for time aggregation")

    parsed = pd.to_datetime(result[COL_DATE], errors="coerce")
    result[COL_MONTH] = (
        parsed.dt.to_period("M").dt.to_timestamp().dt.strftime("%Y-%m-%d")
    )
    return result


def _input_quality_flags(df: pd.DataFrame, metric_id: str) -> dict[str, Any]:
    missing_category = [c for c in CATEGORY_COLUMNS if c not in df.columns]
    return {
        "metric_id": metric_id,
        "missing_category_columns": missing_category,
        "has_all_category_columns": len(missing_category) == 0,
    }


def _aggregate_metric(working: pd.DataFrame, metric_id: str) -> pd.DataFrame:
    spec = METRIC_SPECS[metric_id]
    value_col: str = spec["value_column"]

    if metric_id == "aov":
        grouped = (
            working.groupby(list(GROUP_BY), dropna=False, as_index=False)
            .agg({COL_GMV: "sum", COL_ORDERS: "sum"})
        )
        grouped[value_col] = grouped.apply(
            lambda row: (
                None
                if pd.isna(row[COL_ORDERS])
                or row[COL_ORDERS] == 0
                or pd.isna(row[COL_GMV])
                else float(row[COL_GMV]) / float(row[COL_ORDERS])
            ),
            axis=1,
        )
        return grouped[[COL_SITE, COL_MONTH, value_col]]

    source_col = spec["required_source"][0]
    grouped = (
        working.groupby(list(GROUP_BY), dropna=False, as_index=False)
        .agg({source_col: "sum"})
        .rename(columns={source_col: value_col})
    )
    return grouped


def compute(params: ComputeParams, frame: ScopedFrame) -> dict[str, pd.DataFrame]:
    metric_id = params.metric_id
    if metric_id not in METRIC_SPECS:
        raise ValueError(f"Unknown metric_id={metric_id}; expected gmv|orders|aov")

    _validate_required_columns(frame, metric_id)

    working = _normalize_month_column(frame.data)
    result = _aggregate_metric(working, metric_id)
    result = result.sort_values([COL_SITE, COL_MONTH]).reset_index(drop=True)

    table_id = METRIC_SPECS[metric_id]["table_id"]
    result.attrs["scope_label"] = frame.scope_label
    result.attrs["scope_spec"] = frame.scope_spec
    result.attrs["source_id"] = frame.source_id
    result.attrs["module_id"] = "monthly_market_trend"
    result.attrs["metric_id"] = metric_id
    result.attrs["input_quality"] = _input_quality_flags(working, metric_id)

    return {table_id: result}


def metric_value_column(metric_id: str) -> str:
    return METRIC_SPECS[metric_id]["value_column"]
