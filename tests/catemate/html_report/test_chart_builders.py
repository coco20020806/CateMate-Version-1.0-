"""Tests for html_report chart builders month axis and label text."""

from __future__ import annotations

import pandas as pd

from catemate.html_report.chart_builders import build_trend_figure
from catemate.html_report.schemas import ChartBinding


def test_trend_figure_formats_grass_month_as_yyyy_mm_category() -> None:
    df = pd.DataFrame(
        {
            "grass_region": ["BR", "BR"],
            "grass_month": ["2026-05-01", "2026-06-01"],
            "orders": [54000.0, 58000.0],
        }
    )
    binding = ChartBinding(
        chart_id="c_trend",
        section_id="s_orders",
        table_id="orders_by_site_month",
        chart_type="trend",
        title="Orders trend",
        x_field="grass_month",
        y_fields=["orders"],
        series_field="grass_region",
    )
    fig = build_trend_figure(df, binding)
    trace = fig.data[0]
    assert list(trace.x) == ["2026-05", "2026-06"]
    assert fig.layout.xaxis.type == "category"
    assert list(fig.layout.xaxis.categoryarray) == ["2026-05", "2026-06"]
    assert trace.mode == "lines+markers"
    assert list(trace.text) == ["54,000", "58,000"]
    assert "text" not in (trace.mode or "")
