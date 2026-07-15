"""monthly_market_trend — three derived tables per active metric."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .compute import COL_MONTH, COL_SITE, METRIC_SPECS, metric_value_column

SUFFIX_LATEST = "_latest_month_by_site"
SUFFIX_PCT = "_latest_month_pct_by_site"
SUFFIX_MOM = "_mom_by_site_month"


def _table_ids(metric_id: str) -> tuple[str, str, str]:
    return (
        f"{metric_id}{SUFFIX_LATEST}",
        f"{metric_id}{SUFFIX_PCT}",
        f"{metric_id}{SUFFIX_MOM}",
    )


def _latest_period_slice(
    source: pd.DataFrame,
    *,
    period_column: str,
    value_column: str,
) -> pd.DataFrame:
    if source.empty:
        return pd.DataFrame(columns=[COL_SITE, value_column])

    latest = source[period_column].max()
    cols = [COL_SITE, value_column]
    if value_column not in source.columns:
        return pd.DataFrame(columns=cols)

    return (
        source.loc[source[period_column] == latest, cols]
        .copy()
        .reset_index(drop=True)
    )


def _share_of_total(
    source: pd.DataFrame,
    *,
    value_column: str,
    share_column: str,
) -> pd.DataFrame:
    result = source[[COL_SITE, value_column]].copy()
    total = result[value_column].sum(min_count=1)
    if pd.isna(total) or total == 0:
        result[share_column] = pd.NA
    else:
        result[share_column] = result[value_column] / total
    return result


def _growth_pct(current: float, previous: float) -> float | None:
    if pd.isna(current) or pd.isna(previous) or previous == 0:
        return None
    return float(current) / float(previous) - 1.0


def _mom_by_site_month(primary: pd.DataFrame, value_column: str) -> pd.DataFrame:
    mom_col = f"{value_column}_mom_pct"
    if primary.empty:
        return pd.DataFrame(columns=[COL_SITE, COL_MONTH, value_column, mom_col])

    records: list[dict[str, Any]] = []
    for site, grp in primary.groupby(COL_SITE, sort=False):
        ordered = grp.sort_values(COL_MONTH)
        previous: float | None = None
        for _, row in ordered.iterrows():
            current = row[value_column]
            records.append(
                {
                    COL_SITE: site,
                    COL_MONTH: row[COL_MONTH],
                    value_column: current,
                    mom_col: (
                        _growth_pct(current, previous)
                        if previous is not None
                        else None
                    ),
                }
            )
            if not pd.isna(current):
                previous = float(current)

    return pd.DataFrame(records)


def _resolve_metric_id(primary_tables: dict[str, pd.DataFrame]) -> str:
    for table_id, df in primary_tables.items():
        if "metric_id" in df.attrs:
            return str(df.attrs["metric_id"])
        for metric_id, spec in METRIC_SPECS.items():
            if spec["table_id"] == table_id:
                return metric_id
    raise ValueError("Cannot resolve metric_id from primary_tables")


def transform(
    primary_tables: dict[str, pd.DataFrame],
    derived_specs: list[dict[str, Any]] | None = None,
) -> dict[str, pd.DataFrame]:
    _ = derived_specs

    metric_id = _resolve_metric_id(primary_tables)
    spec = METRIC_SPECS[metric_id]
    primary = primary_tables[spec["table_id"]]
    value_column = metric_value_column(metric_id)
    share_column = f"{value_column}_pct"
    scope_label = primary.attrs.get("scope_label", "")

    latest_id, pct_id, mom_id = _table_ids(metric_id)

    latest = _latest_period_slice(
        primary,
        period_column=COL_MONTH,
        value_column=value_column,
    )
    latest.attrs["scope_label"] = scope_label
    latest.attrs["metric_id"] = metric_id

    pct = _share_of_total(latest, value_column=value_column, share_column=share_column)
    pct.attrs["scope_label"] = scope_label
    pct.attrs["metric_id"] = metric_id

    mom = _mom_by_site_month(primary, value_column=value_column)
    mom.attrs["scope_label"] = scope_label
    mom.attrs["metric_id"] = metric_id

    return {latest_id: latest, pct_id: pct, mom_id: mom}
