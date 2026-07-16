"""Tests for V2 contract loader active_only filtering."""

from __future__ import annotations

from catemate.planning.context_loader import load_v2_data_module_contracts


def test_active_only_returns_two_modules() -> None:
    modules = load_v2_data_module_contracts(active_only=True)
    ids = {m["module_id"] for m in modules}
    assert ids == {"monthly_market_trend", "top_sku_info"}


def test_active_only_false_returns_all_contracts() -> None:
    modules = load_v2_data_module_contracts(active_only=False)
    ids = {m["module_id"] for m in modules}
    assert "daily_cncb_performance" in ids
    assert "keywords" in ids
    assert len(ids) >= 7
