"""Tests for workbook digest compaction."""

from __future__ import annotations

import pandas as pd

from catemate.conclusion_brief.workbook_digest import digest_table


def test_digest_trend_table_recent_periods() -> None:
    df = pd.DataFrame(
        {
            "grass_region": ["SG"] * 4,
            "grass_month": ["2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01"],
            "orders": [100.0, 110.0, 105.0, 120.0],
            "orders_mom_pct": [None, 0.1, -0.05, 0.14],
        }
    )
    digest = digest_table("orders_by_site_month", df, section_id="s_orders", max_rows=10)
    assert digest["table_kind"] == "trend"
    assert digest["section_id"] == "s_orders"
    assert digest["row_count"] == 4
    assert len(digest["recent_periods"]) == 3
    assert "latest_mom" in digest
    assert "metric_range" in digest


def test_digest_rank_table_top_five() -> None:
    df = pd.DataFrame(
        {
            "rank": list(range(1, 8)),
            "item_name": [f"item_{i}" for i in range(1, 8)],
            "orders": [float(100 - i) for i in range(7)],
        }
    )
    digest = digest_table("top_sku", df, max_rows=10)
    assert digest["table_kind"] == "ranked"
    assert len(digest["top_rows"]) == 5


def test_digest_share_table_top_segments() -> None:
    df = pd.DataFrame(
        {
            "grass_region": ["SG", "SG", "SG"],
            "orders_pct": [0.5, 0.3, 0.2],
            "orders": [100.0, 60.0, 40.0],
        }
    )
    digest = digest_table("orders_pct", df, max_rows=10)
    assert digest["table_kind"] == "share"
    assert len(digest["top_segments"]) == 3


def test_digest_generic_table_sample_rows() -> None:
    df = pd.DataFrame({"a": list(range(15)), "b": list(range(15, 30))})
    digest = digest_table("generic_table", df, max_rows=10)
    assert digest["table_kind"] == "generic"
    assert len(digest["sample_rows"]) == 10
