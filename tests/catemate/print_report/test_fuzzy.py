"""Unit tests for print_report fuzzy rules."""

from __future__ import annotations

from catemate.print_report.fuzzy import (
    format_price_range_label,
    fuzzy_metric,
    fuzzy_money,
    fuzzy_orders,
    fuzzy_percent,
    relative_share,
)


def test_fuzzy_percent_buckets() -> None:
    assert fuzzy_percent(0.03) == "<5%"
    assert fuzzy_percent(0.12) == "10%-20%"
    assert fuzzy_percent(12) == "10%-20%"
    assert fuzzy_percent(105) == ">100%"


def test_fuzzy_money_buckets() -> None:
    assert fuzzy_money(100) == "<$5K"
    assert fuzzy_money(12_000) == "$5K-$50K"
    assert fuzzy_money(80_000) == "$50K-$200K"
    assert fuzzy_money(500_000) == "$200K-$1M"
    assert fuzzy_money(2_000_000) == "$1M-$5M"
    assert fuzzy_money(9_000_000) == ">$5M"


def test_fuzzy_orders_buckets() -> None:
    assert fuzzy_orders(50) == "<100"
    assert fuzzy_orders(500) == "100-1K"
    assert fuzzy_orders(5_000) == "1K-10K"


def test_fuzzy_metric_infers_kind() -> None:
    money = fuzzy_metric("gmv_usd", 80_000)
    assert money.display == "$50K-$200K"
    assert money.raw_suppressed is True
    pct = fuzzy_metric("orders_pct", 0.22)
    assert pct.display == "20%-30%"
    orders = fuzzy_metric("ADO", 2_000)
    assert orders.display == "1K-10K"


def test_price_range_label_strips_prefix() -> None:
    assert format_price_range_label("01_[0,1)") == "[0,1)"
    assert format_price_range_label("[1,2)") == "[1,2)"


def test_relative_share() -> None:
    assert relative_share([50, 50]) == [50.0, 50.0]
    assert relative_share([0, 0]) == [0.0, 0.0]
