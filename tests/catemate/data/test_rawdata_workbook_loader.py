"""Tests for direct category rawdata workbook loading."""

from __future__ import annotations

from catemate.data.rawdata_workbook_loader import category_rawdata_available, load_category_rawdata_table
from catemate.scope.filters import apply_scope_filters
from catemate.scope.schemas import ScopeSpec


def test_category_rawdata_available_for_dashboard_history() -> None:
    assert category_rawdata_available("dashboard_history")


def test_load_category_monthly_workbook() -> None:
    df, meta = load_category_rawdata_table("dashboard_history")
    assert meta["source"] == "rawdata_workbook"
    assert len(df) > 1000
    assert "grass_region" in df.columns
    assert "cb_level1_global_be_category" in df.columns


def test_scope_filter_vn_pets_l1_from_rawdata() -> None:
    df, _ = load_category_rawdata_table("dashboard_history")
    spec = ScopeSpec(
        grain="category",
        table_id="dashboard_history",
        target_sites=["VN"],
        category_l1="Pets",
    )
    filtered = apply_scope_filters(df, spec)
    assert len(filtered) > 0
    assert set(filtered["cb_level1_global_be_category"].astype(str)) == {"Pets"}
