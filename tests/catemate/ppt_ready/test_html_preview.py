"""Tests for PPT-ready HTML preview fixes (month axis, site tabs, label toggle)."""

from __future__ import annotations

from pathlib import Path

from catemate.ppt_ready.html_preview import (
    choose_chart_config,
    render_html,
    write_ppt_ready_html_preview,
)
from catemate.ppt_ready.schemas import (
    PptReadyBuildContext,
    PptReadySheetSpec,
    PptReadyWorkbookBuildResult,
)


def _trend_sheet() -> PptReadySheetSpec:
    return PptReadySheetSpec(
        sheet_name="gmv_trend",
        chart_id="chart_gmv_trend",
        chart_title="智能喂食器各站点GMV月度趋势",
        chart_type="trend",
        data_module_id="monthly_market_trend",
        source_table_ids=["gmv_by_site_month"],
        rows=[
            {"grass_region": "AR", "grass_month": "2025-03-01", "gmv_usd": 100.0},
            {"grass_region": "AR", "grass_month": "2025-04-01", "gmv_usd": 120.0},
            {"grass_region": "BR", "grass_month": "2025-03-01", "gmv_usd": 200.0},
            {"grass_region": "BR", "grass_month": "2025-04-01", "gmv_usd": 220.0},
        ],
        output_status="generated",
    )


def _top_sku_sheet() -> PptReadySheetSpec:
    rows = []
    for site in ("AR", "BR", "PH"):
        for rank in range(1, 4):
            rows.append(
                {
                    "grass_region": site,
                    "grass_month": "2025-04-01",
                    "rank": rank,
                    "item_name": f"{site} long item name number {rank} " + ("x" * 40),
                    "gmv_usd": 1000 - rank,
                    "orders": 50 - rank,
                }
            )
    return PptReadySheetSpec(
        sheet_name="top_sku",
        chart_id="chart_top_sku",
        chart_title="热销SKU",
        chart_type="table",
        data_module_id="top_sku_info",
        source_table_ids=["top_sku_by_gmv_top5"],
        rows=rows,
        output_status="generated",
    )


def test_trend_preview_uses_yyyy_mm_category_axis() -> None:
    preview = choose_chart_config(_trend_sheet(), max_rows=1000)
    assert preview.render_mode == "line"
    assert preview.plotly_payload is not None
    x_vals = preview.plotly_payload["data"][0]["x"]
    assert x_vals == ["2025-03", "2025-04"]
    assert preview.plotly_payload["layout"]["xaxis"]["type"] == "category"
    assert preview.plotly_payload["layout"]["xaxis"]["categoryarray"] == ["2025-03", "2025-04"]
    assert "text" in preview.plotly_payload["data"][0]
    assert preview.plotly_payload["data"][0]["mode"] == "lines+markers"
    assert "textposition" not in preview.plotly_payload["data"][0]


def test_table_preview_builds_site_tabs() -> None:
    preview = choose_chart_config(_top_sku_sheet(), max_rows=1000)
    assert preview.render_mode == "table"
    sites = [tab.site for tab in preview.site_tabs]
    assert sites == ["AR", "BR", "PH"]
    assert all(len(tab.rows) == 3 for tab in preview.site_tabs)


def test_html_contains_site_tabs_and_label_toggle(tmp_path: Path) -> None:
    result = PptReadyWorkbookBuildResult(
        case_id="demo",
        output_path=tmp_path / "ppt_ready_demo.xlsx",
        sheets=[_trend_sheet(), _top_sku_sheet()],
    )
    context = PptReadyBuildContext(
        case_id="demo",
        planning_spec_path=tmp_path / "planning.json",
        requirement_workbook_path=tmp_path / "req.xlsx",
        processed_manifest_path=tmp_path / "manifest.yaml",
        processed_data_dir=tmp_path,
    )
    out = tmp_path / "preview.html"
    write_ppt_ready_html_preview(result, context, out, max_rows=1000)
    html = out.read_text(encoding="utf-8")
    assert "2025-03" in html
    assert "显示数字" in html
    assert "cmToggleChartLabels" in html
    assert "cmSwitchSiteTab" in html
    assert 'data-target="site-' in html
    assert "col-item_name" in html
    assert ">BR<" in html or ">BR</button>" in html
    assert ">PH<" in html or ">PH</button>" in html


def test_render_html_label_toggle_markup() -> None:
    preview = choose_chart_config(_trend_sheet(), max_rows=100)
    result = PptReadyWorkbookBuildResult(
        case_id="demo",
        output_path=Path("out.xlsx"),
        sheets=[_trend_sheet()],
    )
    context = PptReadyBuildContext(
        case_id="demo",
        planning_spec_path=Path("p.json"),
        requirement_workbook_path=Path("r.xlsx"),
        processed_manifest_path=Path("m.yaml"),
        processed_data_dir=Path("."),
    )
    html = render_html(result=result, context=context, previews=[preview])
    assert "label-toggle" in html
    assert "显示数字" in html
