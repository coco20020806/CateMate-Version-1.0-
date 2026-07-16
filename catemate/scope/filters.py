"""Deterministic row filters for Scope executor."""

from __future__ import annotations

import pandas as pd

from catemate.scope.schemas import ScopeSpec

SITE_COLUMNS = ("grass_region", "region", "site")
CATEGORY_COLUMNS = (
    "cb_level1_global_be_category",
    "level2_global_be_category",
    "level3_global_be_category",
)


def apply_scope_filters(df: pd.DataFrame, spec: ScopeSpec) -> pd.DataFrame:
    """Filter processed rows by site, category, and optional extra filters."""
    result = df.copy()

    if spec.target_sites:
        site_col = _first_present_column(result, SITE_COLUMNS)
        if site_col:
            sites = {s.strip().upper() for s in spec.target_sites if s.strip()}
            result = result[
                result[site_col].astype(str).str.strip().str.upper().isin(sites)
            ]

    if spec.category_l1:
        result = _filter_category_level(result, CATEGORY_COLUMNS[0], spec.category_l1)
    if spec.category_l2:
        result = _filter_category_level(result, CATEGORY_COLUMNS[1], spec.category_l2)
    if spec.category_l3:
        result = _filter_category_level(result, CATEGORY_COLUMNS[2], spec.category_l3)

    for key, value in spec.extra_filters.items():
        if key in result.columns and value not in (None, ""):
            result = result[result[key].astype(str) == str(value)]

    return result.reset_index(drop=True)


def _first_present_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _filter_category_level(df: pd.DataFrame, column: str, value: str) -> pd.DataFrame:
    if column not in df.columns or not value.strip():
        return df
    needle = value.strip().lower()
    return df[df[column].astype(str).str.strip().str.lower() == needle]
