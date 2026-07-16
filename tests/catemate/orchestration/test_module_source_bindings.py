"""Tests for module source_bindings resolution."""

from __future__ import annotations

import pytest

from catemate.orchestration.module_source_bindings import (
    allowed_grains,
    get_source_bindings,
    resolve_table_id,
    validate_run_source,
)


def test_monthly_market_trend_allows_three_grains() -> None:
    grains = allowed_grains("monthly_market_trend")
    assert grains == ["category", "shop", "item"]


def test_top_listing_only_item_grain() -> None:
    grains = allowed_grains("top_listing")
    assert grains == ["item"]


def test_resolve_table_id_category_dashboard_history() -> None:
    table_id = resolve_table_id("monthly_market_trend", "category")
    assert table_id in {"dashboard_history", "rm_raw_data"}


def test_validate_run_source_rejects_invalid_grain() -> None:
    assert not validate_run_source("keywords", "shop", "shop_monthly_sales")


def test_resolve_table_id_rejects_invalid_grain() -> None:
    with pytest.raises(ValueError, match="does not allow grain"):
        resolve_table_id("keywords", "shop")


def test_get_source_bindings_has_loader_modes() -> None:
    bindings = get_source_bindings("monthly_market_trend")
    assert bindings["by_grain"]["item"]["loader"] == "category_folder"
    assert bindings["by_grain"]["category"]["loader"] == "flat_workbook"
