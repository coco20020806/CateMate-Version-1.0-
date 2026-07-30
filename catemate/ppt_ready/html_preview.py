"""Generate offline-openable HTML chart preview from PPT-ready build result."""

from __future__ import annotations

import html
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from catemate.orchestration.module_registry import is_active_v2_module
from catemate.ppt_ready.field_utils import (
    looks_like_gmv_orders_trend,
    price_range_sort_key,
    resolve_trend_time_fields,
    sort_by_price_range,
)
from catemate.ppt_ready.schemas import (
    PptReadyBuildContext,
    PptReadySheetSpec,
    PptReadyWorkbookBuildResult,
)


X_TIME_FIELDS = ["grass_month", "year_month", "month", "date", "grass_date"]
Y_METRIC_FIELDS = [
    "gmv_usd",
    "orders",
    "shopee_gmv_usd(SUM)",
    "shopee_order(SUM)",
    "cncb_gmv_usd(SUM)",
    "cncb_order(SUM)",
    "ADG",
    "ADO",
    "current_adgmv(RAW)",
    "current_ado(RAW)",
    "aov",
    "share",
]
SERIES_FIELDS = ["grass_region", "region", "site"]
BAR_X_FIELDS = [
    "Price_Range_USD",
    "level3_global_be_category",
    "grass_region",
    "keyword",
    "shop_id",
    "level2_global_be_category",
    "cb_level1_global_be_category",
]
SHARE_VALUE_HINTS = ("share", "proportion", "rate", "ratio")
TABLE_PREFERRED = [
    "item_name",
    "item_link",
    "item_image",
    "item_price_usd",
    "keyword",
    "shop_id",
    "shop_link",
    "ggp_account_name",
    "user_name",
    "current_ado(RAW)",
    "current_adgmv(RAW)",
    "grass_region",
    "cb_level1_global_be_category",
    "level2_global_be_category",
    "level3_global_be_category",
    "Price_Range_USD",
]
SAMPLE_TABLE_ROWS = 20
MAX_TREND_SERIES = 8
MAX_BAR_CATEGORIES = 15
SHARE_PIE_LIMIT = 8
SHARE_BAR_TOP = 10


@dataclass
class SiteTableTab:
    site: str
    headers: list[str]
    rows: list[list[Any]]


@dataclass
class ChartPreviewSpec:
    chart_id: str
    title: str
    chart_type: str
    output_status: str
    render_mode: str  # line / pie / bar / hbar / table / unsupported / hidden
    plotly_payload: dict[str, Any] | None = None
    preview_notes: list[str] = field(default_factory=list)
    sample_headers: list[str] = field(default_factory=list)
    sample_rows: list[list[Any]] = field(default_factory=list)
    site_tabs: list[SiteTableTab] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)
    hidden: bool = False
    replaced_by: str = ""


def write_ppt_ready_html_preview(
    result: PptReadyWorkbookBuildResult,
    context: PptReadyBuildContext,
    output_path: Path,
    *,
    max_rows: int = 1000,
) -> Path:
    """Write HTML preview from in-memory build result (does not re-read xlsx)."""
    previews = [
        choose_chart_config(sheet, max_rows=max_rows) for sheet in result.sheets
    ]
    previews = deduplicate_redundant_trend_previews(result.sheets, previews)
    html_text = render_html(result=result, context=context, previews=previews)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def choose_chart_config(sheet: PptReadySheetSpec, *, max_rows: int) -> ChartPreviewSpec:
    meta = {
        "source_workbook": "; ".join(sheet.source_workbook_names),
        "source_sheet": "; ".join(sheet.source_sheets),
        "processed_csv": "; ".join(sheet.processed_csv_paths),
        "source_rule_note": sheet.source_rule_note or "",
        "missing_data_note": sheet.missing_data_note or "",
        "null_reason_note": sheet.null_reason_note or "",
        "data_module_id": sheet.data_module_id or "",
        "sheet_name": sheet.sheet_name,
        "source_table_ids": "; ".join(sheet.source_table_ids),
    }
    rows = _usable_rows(sheet.rows, max_rows=max_rows)
    sample_headers, sample_rows = render_table_sample(sheet, rows)
    site_tabs = build_site_table_tabs(rows)

    base = ChartPreviewSpec(
        chart_id=sheet.chart_id,
        title=sheet.chart_title or sheet.chart_id,
        chart_type=sheet.chart_type,
        output_status=sheet.output_status,
        render_mode="table",
        sample_headers=sample_headers,
        sample_rows=sample_rows,
        site_tabs=site_tabs,
        meta=meta,
    )

    if sheet.output_status in {"unsupported", "empty"} or not rows:
        base.render_mode = "unsupported" if sheet.output_status == "unsupported" else "table"
        if sheet.output_status == "unsupported":
            base.preview_notes.append(
                sheet.missing_data_note
                or sheet.source_rule_note
                or "unsupported chart; table sample only"
            )
        elif not rows:
            base.preview_notes.append("No plottable rows for preview.")
        return base

    chart_type = (sheet.chart_type or "").lower()
    if chart_type == "trend":
        return _build_trend_preview(base, sheet, rows, max_rows=max_rows)
    if chart_type == "share":
        return _build_share_preview(base, rows, max_rows=max_rows)
    if chart_type == "bar":
        return _build_bar_preview(base, rows, max_rows=max_rows)
    if chart_type == "table":
        base.render_mode = "table"
        base.preview_notes.append("table chart_type: readable table preview only.")
        if site_tabs:
            base.preview_notes.append(
                f"Table preview grouped by site ({len(site_tabs)} sites); "
                f"up to {SAMPLE_TABLE_ROWS} rows per site."
            )
        return base

    base.render_mode = "unsupported"
    base.preview_notes.append(f"preview has no dedicated renderer for chart_type={sheet.chart_type!r}")
    return base


def deduplicate_redundant_trend_previews(
    sheets: list[PptReadySheetSpec],
    previews: list[ChartPreviewSpec],
) -> list[ChartPreviewSpec]:
    """Hide near-duplicate monthly GMV/Orders trends; keep the longer coverage chart."""
    by_id = {p.chart_id: idx for idx, p in enumerate(previews)}
    sheet_by_id = {s.chart_id: s for s in sheets}

    candidates: list[tuple[str, PptReadySheetSpec, ChartPreviewSpec]] = []
    for preview in previews:
        sheet = sheet_by_id.get(preview.chart_id)
        if sheet is None:
            continue
        if (sheet.chart_type or "").lower() != "trend":
            continue
        if preview.render_mode == "unsupported":
            continue
        metric_names = []
        if sheet.rows:
            metric_names = [k for k in sheet.rows[0].keys() if k in Y_METRIC_FIELDS]
        if not looks_like_gmv_orders_trend(metric_names, sheet.chart_title):
            continue
        # Exclude daily charts from this monthly duplicate group.
        _, is_daily, _ = resolve_trend_time_fields(
            table_ids=sheet.source_table_ids,
            source_sheets=sheet.source_sheets,
            chart_id=sheet.chart_id,
            chart_title=sheet.chart_title,
            force_monthly=is_active_v2_module(sheet.data_module_id or ""),
        )
        if is_daily:
            continue
        candidates.append((preview.chart_id, sheet, preview))

    if len(candidates) < 2:
        return previews

    scored: list[tuple[tuple, str]] = []
    for chart_id, sheet, preview in candidates:
        score = _trend_coverage_score(sheet, preview)
        scored.append((score, chart_id))
    scored.sort(reverse=True)
    keep_id = scored[0][1]
    keep_preview = previews[by_id[keep_id]]

    for _, chart_id in scored[1:]:
        idx = by_id[chart_id]
        hidden = previews[idx]
        hidden.hidden = True
        hidden.replaced_by = keep_id
        hidden.render_mode = "hidden"
        hidden.plotly_payload = None
        hidden.preview_notes = [
            (
                f"重复图表已降级：与「{keep_preview.title}」({keep_id}) 表达同类月度 "
                "GMV/Orders 趋势含义，但来源表不同。"
            ),
            (
                f"预览保留「{keep_preview.title}」，因其时间窗口更长或数据覆盖更完整"
                "（优先 rm_raw_data）。"
            ),
            "本 section 仅保留说明与数据样例，不渲染折线图。",
        ]
    return previews


def _trend_coverage_score(sheet: PptReadySheetSpec, preview: ChartPreviewSpec) -> tuple:
    """Higher is better. Prefer longer time span, then more rows, then rm_raw_data."""
    rows = _usable_rows(sheet.rows, max_rows=50000)
    available = set(rows[0].keys()) if rows else set()
    time_field = None
    for name in X_TIME_FIELDS:
        if name in available:
            time_field = name
            break
    distinct = set()
    if time_field:
        for row in rows:
            value = row.get(time_field)
            if value is not None and str(value).strip():
                distinct.add(str(value))
    prefers_rm = 1 if "rm_raw_data" in sheet.source_table_ids else 0
    return (len(distinct), len(rows), prefers_rm, sheet.chart_id)

def render_table_sample(
    sheet: PptReadySheetSpec,
    rows: list[dict[str, Any]] | None = None,
) -> tuple[list[str], list[list[Any]]]:
    data = rows if rows is not None else _usable_rows(sheet.rows, max_rows=SAMPLE_TABLE_ROWS)
    if not data:
        return [], []
    if "Price_Range_USD" in data[0]:
        data = sorted(data, key=lambda row: price_range_sort_key(row.get("Price_Range_USD")))
    headers = _table_headers_for_rows(data)
    sample = []
    for row in data[:SAMPLE_TABLE_ROWS]:
        sample.append([row.get(h) for h in headers])
    return headers, sample


def _table_headers_for_rows(data: list[dict[str, Any]]) -> list[str]:
    preferred = [c for c in TABLE_PREFERRED if c in data[0]]
    extras = [k for k in data[0].keys() if k not in preferred and k != "builder_notes"]
    return (preferred + extras)[:12]


def build_site_table_tabs(rows: list[dict[str, Any]]) -> list[SiteTableTab]:
    """Group table rows by site; keep up to SAMPLE_TABLE_ROWS per site."""
    if not rows:
        return []
    available = set(rows[0].keys())
    site_field = _first_present(SERIES_FIELDS, available)
    if site_field is None:
        return []

    by_site: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        raw = row.get(site_field)
        site = str(raw) if raw is not None and str(raw).strip() else "(blank)"
        by_site[site].append(row)

    if len(by_site) < 2:
        return []

    headers = _table_headers_for_rows(rows)
    tabs: list[SiteTableTab] = []
    for site in sorted(by_site.keys()):
        site_rows = by_site[site]
        if "Price_Range_USD" in site_rows[0]:
            site_rows = sorted(
                site_rows, key=lambda row: price_range_sort_key(row.get("Price_Range_USD"))
            )
        sample = [[row.get(h) for h in headers] for row in site_rows[:SAMPLE_TABLE_ROWS]]
        tabs.append(SiteTableTab(site=site, headers=headers, rows=sample))
    return tabs


def _usable_rows(rows: list[dict[str, Any]], *, max_rows: int) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # Skip notes-only placeholder rows.
        if set(row.keys()) <= {"note", "builder_notes"} and "note" in row:
            continue
        cleaned.append(row)
        if len(cleaned) >= max_rows:
            break
    return cleaned


def _first_present(keys: list[str], available: set[str]) -> str | None:
    for key in keys:
        if key in available:
            return key
    return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _parse_time_value(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt, size in (("%Y-%m-%d", 10), ("%Y/%m/%d", 10), ("%Y-%m", 7), ("%Y/%m", 7)):
        try:
            return datetime.strptime(text[:size], fmt)
        except ValueError:
            continue
    return None


def _format_trend_x(value: Any, *, is_daily: bool) -> str:
    """Format trend x labels so Plotly does not invent day/week ticks for monthly data."""
    parsed = _parse_time_value(value)
    if parsed is None:
        return "" if value is None else str(value)
    if is_daily:
        return parsed.strftime("%Y-%m-%d")
    return parsed.strftime("%Y-%m")


def _sort_time_key(value: Any) -> str:
    parsed = _parse_time_value(value)
    if parsed is not None:
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    return "" if value is None else str(value)


def _format_metric_label(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{value:,.0f}"
    if abs(value) >= 100:
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def _build_trend_preview(
    base: ChartPreviewSpec,
    sheet: PptReadySheetSpec,
    rows: list[dict[str, Any]],
    *,
    max_rows: int,
) -> ChartPreviewSpec:
    available = set(rows[0].keys())
    time_candidates, is_daily, daily_note = resolve_trend_time_fields(
        table_ids=sheet.source_table_ids,
        source_sheets=sheet.source_sheets,
        chart_id=sheet.chart_id,
        chart_title=sheet.chart_title,
        force_monthly=is_active_v2_module(sheet.data_module_id or ""),
    )
    x_field = _first_present(time_candidates, available)
    y_field = _first_present(Y_METRIC_FIELDS, available)
    series_field = _first_present(SERIES_FIELDS, available)

    if x_field is None or y_field is None:
        base.render_mode = "table"
        base.preview_notes.append(
            f"trend preview degraded to table: missing x/y "
            f"(x={x_field}, y={y_field})."
        )
        return base

    if is_daily and daily_note:
        base.preview_notes.append(daily_note)

    points: list[tuple[Any, float, str]] = []
    for row in rows:
        y_val = _to_float(row.get(y_field))
        if y_val is None:
            continue
        series = str(row.get(series_field)) if series_field and row.get(series_field) is not None else "all"
        points.append((row.get(x_field), y_val, series))

    if not points:
        base.render_mode = "table"
        base.preview_notes.append("trend preview degraded to table: no numeric y values.")
        return base

    # Rank series by total metric; keep top N.
    series_total: dict[str, float] = defaultdict(float)
    for _, y_val, series in points:
        series_total[series] += y_val
    ranked = sorted(series_total.items(), key=lambda item: item[1], reverse=True)
    keep = {name for name, _ in ranked[:MAX_TREND_SERIES]}
    if len(ranked) > MAX_TREND_SERIES:
        base.preview_notes.append(
            f"Preview limited to top {MAX_TREND_SERIES} series by {y_field}."
        )

    by_series: dict[str, list[tuple[Any, float]]] = defaultdict(list)
    for x_val, y_val, series in points:
        if series not in keep:
            continue
        by_series[series].append((x_val, y_val))

    traces = []
    category_labels: list[str] = []
    seen_labels: set[str] = set()
    for series, values in by_series.items():
        values.sort(key=lambda item: _sort_time_key(item[0]))
        agg: dict[str, float] = defaultdict(float)
        order_labels: list[str] = []
        for x_val, y_val in values:
            label = _format_trend_x(x_val, is_daily=is_daily)
            if label not in agg:
                order_labels.append(label)
            agg[label] += y_val
            if label and label not in seen_labels:
                seen_labels.add(label)
                category_labels.append(label)
        y_vals = [agg[label] for label in order_labels]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": series,
                "x": order_labels,
                "y": y_vals,
                "text": [_format_metric_label(v) for v in y_vals],
            }
        )

    # Keep category order chronological across series.
    category_labels.sort(key=_sort_time_key)

    if len(points) >= max_rows:
        base.preview_notes.append(f"Preview input limited to first {max_rows} rows.")

    base.render_mode = "line"
    base.plotly_payload = {
        "data": traces,
        "layout": {
            "title": {"text": base.title, "x": 0.01},
            "xaxis": {
                "title": x_field,
                "type": "category",
                "categoryorder": "array",
                "categoryarray": category_labels,
            },
            "yaxis": {"title": y_field},
            "margin": {"l": 60, "r": 20, "t": 50, "b": 60},
            "legend": {"orientation": "h"},
            "height": 380,
        },
    }
    base.preview_notes.append(f"line chart: x={x_field}, y={y_field}, series={series_field or 'all'}")
    return base


def _pick_dimension(available: set[str], preferred: list[str]) -> str | None:
    found = _first_present(preferred, available)
    if found:
        return found
    skip = set(Y_METRIC_FIELDS) | {"builder_notes", "note", "aov", "share"}
    for key in available:
        if key not in skip:
            return key
    return None


def _build_share_preview(
    base: ChartPreviewSpec,
    rows: list[dict[str, Any]],
    *,
    max_rows: int,
) -> ChartPreviewSpec:
    available = set(rows[0].keys())
    share_field = None
    for key in available:
        lowered = key.lower()
        if any(hint in lowered for hint in SHARE_VALUE_HINTS):
            share_field = key
            break
    metric_field = share_field or _first_present(Y_METRIC_FIELDS, available)
    dim_field = _pick_dimension(
        available,
        ["Price_Range_USD", "level3_global_be_category", "grass_region", "keyword", "shop_id"],
    )

    if metric_field is None or dim_field is None:
        base.render_mode = "table"
        base.preview_notes.append("share preview degraded to table: missing dimension/metric.")
        return base

    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        value = _to_float(row.get(metric_field))
        if value is None:
            continue
        label = str(row.get(dim_field) if row.get(dim_field) is not None else "(blank)")
        totals[label] += value

    if not totals:
        base.render_mode = "table"
        base.preview_notes.append("share preview degraded to table: no numeric values.")
        return base

    preview_computed = share_field is None
    if preview_computed:
        total = sum(totals.values())
        if total <= 0:
            base.render_mode = "table"
            base.preview_notes.append("share preview degraded: metric total is zero/NA.")
            return base
        shares = {k: v / total for k, v in totals.items()}
        base.preview_notes.append(
            f"preview computed share from {metric_field}; workbook source data not modified"
        )
    else:
        shares = dict(totals)

    ranked = sort_by_price_range(list(shares.items())) if dim_field == "Price_Range_USD" else sorted(
        shares.items(), key=lambda item: item[1], reverse=True
    )
    if dim_field == "Price_Range_USD":
        base.preview_notes.append("Sorted by Price_Range_USD natural order (not by share/metric desc).")
        if len(ranked) > max(SHARE_PIE_LIMIT, SHARE_BAR_TOP):
            ranked = ranked[: max(SHARE_PIE_LIMIT, SHARE_BAR_TOP)]
            base.preview_notes.append(
                f"Preview limited to first {max(SHARE_PIE_LIMIT, SHARE_BAR_TOP)} price bands in natural order."
            )
        labels = [k for k, _ in ranked]
        values = [v for _, v in ranked]
        if len(ranked) <= SHARE_PIE_LIMIT:
            base.render_mode = "pie"
            base.plotly_payload = {
                "data": [
                    {
                        "type": "pie",
                        "labels": labels,
                        "values": values,
                        "hole": 0.25,
                        "sort": False,
                        "text": [_format_metric_label(v) for v in values],
                        "textinfo": "none",
                        "hovertemplate": "%{label}: %{value}<extra></extra>",
                    }
                ],
                "layout": {"title": {"text": base.title, "x": 0.01}, "height": 400, "margin": {"t": 50}},
            }
        else:
            base.render_mode = "hbar"
            # Keep natural price order with low band at top.
            base.plotly_payload = {
                "data": [
                    {
                        "type": "bar",
                        "orientation": "h",
                        "y": labels,
                        "x": values,
                        "text": [_format_metric_label(v) for v in values],
                        "textposition": "none",
                    }
                ],
                "layout": {
                    "title": {"text": base.title, "x": 0.01},
                    "xaxis": {"title": metric_field if preview_computed else share_field},
                    "yaxis": {"autorange": "reversed"},
                    "height": 420,
                    "margin": {"l": 140, "r": 20, "t": 50, "b": 40},
                },
            }
    elif len(ranked) <= SHARE_PIE_LIMIT:
        labels = [k for k, _ in ranked]
        values = [v for _, v in ranked]
        base.render_mode = "pie"
        base.plotly_payload = {
            "data": [
                {
                    "type": "pie",
                    "labels": labels,
                    "values": values,
                    "hole": 0.25,
                    "text": [_format_metric_label(v) for v in values],
                    "textinfo": "none",
                    "hovertemplate": "%{label}: %{value}<extra></extra>",
                }
            ],
            "layout": {"title": {"text": base.title, "x": 0.01}, "height": 400, "margin": {"t": 50}},
        }
    else:
        top = ranked[:SHARE_BAR_TOP]
        other = sum(v for _, v in ranked[SHARE_BAR_TOP:])
        labels = [k for k, _ in top] + (["Others"] if other > 0 else [])
        values = [v for _, v in top] + ([other] if other > 0 else [])
        base.render_mode = "hbar"
        base.plotly_payload = {
            "data": [
                {
                    "type": "bar",
                    "orientation": "h",
                    "y": labels[::-1],
                    "x": values[::-1],
                    "text": [_format_metric_label(v) for v in values[::-1]],
                    "textposition": "none",
                }
            ],
            "layout": {
                "title": {"text": base.title, "x": 0.01},
                "xaxis": {"title": metric_field if preview_computed else share_field},
                "height": 420,
                "margin": {"l": 140, "r": 20, "t": 50, "b": 40},
            },
        }
        base.preview_notes.append(
            f"Preview limited to Top {SHARE_BAR_TOP} + Others by {metric_field}."
        )

    if len(rows) >= max_rows:
        base.preview_notes.append(f"Preview input limited to first {max_rows} rows.")
    base.preview_notes.append(f"share chart: dim={dim_field}, value={metric_field}")
    return base


def _build_bar_preview(
    base: ChartPreviewSpec,
    rows: list[dict[str, Any]],
    *,
    max_rows: int,
) -> ChartPreviewSpec:
    available = set(rows[0].keys())
    x_field = _pick_dimension(available, BAR_X_FIELDS)
    y_field = _first_present(Y_METRIC_FIELDS, available)
    if x_field is None or y_field is None:
        base.render_mode = "table"
        base.preview_notes.append(
            f"bar preview degraded to table: missing x/y (x={x_field}, y={y_field})."
        )
        return base

    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        value = _to_float(row.get(y_field))
        if value is None:
            continue
        label = str(row.get(x_field) if row.get(x_field) is not None else "(blank)")
        totals[label] += value
    if not totals:
        base.render_mode = "table"
        base.preview_notes.append("bar preview degraded to table: no numeric y values.")
        return base

    if x_field == "Price_Range_USD":
        ranked = sort_by_price_range(list(totals.items()))
        base.preview_notes.append("Sorted by Price_Range_USD natural order (not by metric desc).")
        if len(ranked) > MAX_BAR_CATEGORIES:
            ranked = ranked[:MAX_BAR_CATEGORIES]
            base.preview_notes.append(
                f"Preview limited to first {MAX_BAR_CATEGORIES} price bands in natural order."
            )
    else:
        ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
        if len(ranked) > MAX_BAR_CATEGORIES:
            ranked = ranked[:MAX_BAR_CATEGORIES]
            base.preview_notes.append(f"Preview limited to top {MAX_BAR_CATEGORIES} by {y_field}.")

    labels = [k for k, _ in ranked]
    values = [v for _, v in ranked]
    base.render_mode = "bar"
    base.plotly_payload = {
        "data": [
            {
                "type": "bar",
                "x": labels,
                "y": values,
                "name": y_field,
                "text": [_format_metric_label(v) for v in values],
                "textposition": "none",
            }
        ],
        "layout": {
            "title": {"text": base.title, "x": 0.01},
            "xaxis": {"title": x_field, "tickangle": -30, "categoryorder": "array", "categoryarray": labels},
            "yaxis": {"title": y_field},
            "height": 400,
            "margin": {"l": 60, "r": 20, "t": 50, "b": 100},
        },
    }
    if len(rows) >= max_rows:
        base.preview_notes.append(f"Preview input limited to first {max_rows} rows.")
    base.preview_notes.append(f"bar chart: x={x_field}, y={y_field}")
    return base


def render_html(
    *,
    result: PptReadyWorkbookBuildResult,
    context: PptReadyBuildContext,
    previews: list[ChartPreviewSpec],
) -> str:
    status_counts: dict[str, int] = defaultdict(int)
    for sheet in result.sheets:
        status_counts[sheet.output_status or "unknown"] += 1

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    visible = [p for p in previews if not p.hidden]
    hidden = [p for p in previews if p.hidden]
    sections = [_render_section(preview, index) for index, preview in enumerate(previews)]
    hidden_block = ""
    if hidden:
        items = "".join(
            f"<li><strong>{esc(p.title)}</strong> ({esc(p.chart_id)}) → replaced by "
            f"<code>{esc(p.replaced_by)}</code></li>"
            for p in hidden
        )
        hidden_block = f"""
<section class="overview">
  <h2 style="font-size:18px;margin:0 0 8px;">Deduplicated / Hidden charts</h2>
  <p style="color:var(--muted);font-size:14px;margin:0 0 8px;">
    以下图表因表达含义与保留图重复，在预览中降级为说明（不渲染折线图）。workbook 数据未删除。
  </p>
  <ul style="margin:0;padding-left:18px;font-size:14px;">{items}</ul>
</section>
"""
    plotly_scripts = _render_plotly_bootstraps(previews)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>CateMate PPT-ready Preview — {esc(result.case_id)}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root {{
  --border: #d9dee7;
  --bg: #f7f8fa;
  --card: #ffffff;
  --text: #1f2937;
  --muted: #6b7280;
  --accent: #2563eb;
  --warn: #b45309;
  --danger: #b91c1c;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--text);
  background: var(--bg);
  line-height: 1.45;
}}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 24px 20px 48px; }}
.cdn-note {{
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
}}
.overview {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 18px 8px;
  margin-bottom: 20px;
}}
.overview h1 {{ margin: 0 0 8px; font-size: 22px; }}
.meta-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 8px 16px;
  margin: 12px 0;
  font-size: 14px;
}}
.meta-grid div span {{ color: var(--muted); display: block; font-size: 12px; }}
.stats {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 12px; }}
.pill {{
  background: #eef2ff;
  color: #3730a3;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 13px;
}}
.section {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
}}
.section.hidden-chart {{ border-style: dashed; opacity: 0.95; }}
.section h2 {{ margin: 0 0 6px; font-size: 18px; }}
.section .sub {{ color: var(--muted); font-size: 13px; margin-bottom: 10px; }}
.badges {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }}
.badge {{
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 12px;
  background: #f8fafc;
}}
.badge.status-unsupported {{ color: var(--danger); border-color: #fecaca; background: #fef2f2; }}
.badge.status-partial {{ color: var(--warn); border-color: #fde68a; background: #fffbeb; }}
.badge.status-hidden {{ color: #6b7280; border-color: #e5e7eb; background: #f9fafb; }}
.notes {{
  background: #f8fafc;
  border-left: 3px solid var(--accent);
  padding: 8px 10px;
  margin: 8px 0 12px;
  font-size: 13px;
}}
.notes.warn {{ border-left-color: var(--warn); }}
.chart-toolbar {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin: 0 0 8px;
}}
.chart-toolbar button, .site-tabs button {{
  border: 1px solid var(--border);
  background: #f8fafc;
  color: var(--text);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}}
.chart-toolbar button:hover, .site-tabs button:hover {{
  border-color: var(--accent);
  color: var(--accent);
}}
.site-tabs {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 10px;
}}
.site-tabs button.active {{
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #3730a3;
}}
.site-panel {{ display: none; }}
.site-panel.active {{ display: block; }}
.chart-box {{ width: 100%; min-height: 120px; }}
.table-wrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }}
table.sample {{
  border-collapse: collapse;
  width: 100%;
  font-size: 12px;
  background: #fff;
}}
table.sample th, table.sample td {{
  border-bottom: 1px solid var(--border);
  padding: 6px 8px;
  text-align: left;
  white-space: nowrap;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
}}
table.sample th.col-item_name,
table.sample td.col-item_name {{
  max-width: 480px;
  min-width: 220px;
  white-space: normal;
  word-break: break-word;
  overflow: visible;
  text-overflow: unset;
  vertical-align: top;
}}
table.sample th {{ background: #f1f5f9; position: sticky; top: 0; }}
img.thumb {{
  width: 36px;
  height: 36px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: #f8fafc;
}}
details.sample-block {{ margin-top: 10px; }}
details.sample-block summary {{
  cursor: pointer;
  color: var(--muted);
  font-size: 13px;
  margin-bottom: 6px;
}}
footer {{ color: var(--muted); font-size: 12px; margin-top: 24px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="cdn-note">需要网络加载 Plotly CDN（cdn.plot.ly）才能渲染交互图表。本页是验收预览，不是正式 PPT。</div>
  <section class="overview">
    <h1>CateMate PPT-ready 图表预览</h1>
    <div class="meta-grid">
      <div><span>case_id</span>{esc(result.case_id)}</div>
      <div><span>generated_at</span>{esc(generated_at)}</div>
      <div><span>workbook</span>{esc(str(result.output_path))}</div>
      <div><span>planning_spec</span>{esc(str(context.planning_spec_path))}</div>
      <div><span>requirement_workbook</span>{esc(str(context.requirement_workbook_path))}</div>
      <div><span>chart_count</span>{len(result.sheets)}</div>
      <div><span>visible charts</span>{len(visible)}</div>
      <div><span>hidden/deduplicated</span>{len(hidden)}</div>
    </div>
    <div class="stats">
      <span class="pill">generated: {status_counts.get("generated", 0)}</span>
      <span class="pill">partial: {status_counts.get("partial", 0)}</span>
      <span class="pill">unsupported: {status_counts.get("unsupported", 0)}</span>
      <span class="pill">empty: {status_counts.get("empty", 0)}</span>
    </div>
  </section>
  {hidden_block}
  {"".join(sections)}
  <footer>Preview-only. Workbook data is not modified. Aggregation / Top-N / dedupe applies only to HTML charts.</footer>
</div>
{plotly_scripts}
</body>
</html>
"""


def _render_section(preview: ChartPreviewSpec, index: int) -> str:
    status_label = "hidden" if preview.hidden else preview.output_status
    status_class = f"status-{esc(status_label)}"
    note_parts = []
    if preview.meta.get("missing_data_note"):
        note_parts.append(f"<div><strong>missing:</strong> {esc(preview.meta['missing_data_note'])}</div>")
    if preview.meta.get("null_reason_note"):
        note_parts.append(f"<div><strong>null:</strong> {esc(preview.meta['null_reason_note'])}</div>")
    for note in preview.preview_notes:
        note_parts.append(f"<div>{esc(note)}</div>")
    if preview.meta.get("source_rule_note"):
        note_parts.append(f"<div><strong>rule:</strong> {esc(preview.meta['source_rule_note'])}</div>")
    notes_html = (
        f"<div class='notes{' warn' if preview.output_status != 'generated' or preview.hidden else ''}'>"
        f"{''.join(note_parts)}</div>"
        if note_parts
        else ""
    )

    chart_html = ""
    if preview.hidden:
        chart_html = (
            "<div class='notes warn'>重复图表已隐藏折线预览；请查看上方 Deduplicated 说明"
            f"或保留图 <code>{esc(preview.replaced_by)}</code>。</div>"
        )
    elif preview.render_mode in {"line", "pie", "bar", "hbar"} and preview.plotly_payload:
        chart_html = (
            f'<div class="chart-toolbar">'
            f'<button type="button" class="label-toggle" data-chart="chart-{index}" data-on="0"'
            f' onclick="window.cmToggleChartLabels(this)">显示数字</button>'
            f"</div>"
            f'<div class="chart-box" id="chart-{index}"></div>'
        )
    elif preview.render_mode == "unsupported":
        chart_html = "<div class='notes warn'>本图未生成图表预览（unsupported / 无法选择字段）。</div>"
    else:
        chart_html = "<div class='notes'>本 section 使用表格预览。</div>"

    table_html = _render_sample_table(preview, section_index=index)
    section_class = "section hidden-chart" if preview.hidden else "section"
    return f"""
<section class="{section_class}" id="{esc(preview.chart_id)}">
  <h2>{esc(preview.title)}</h2>
  <div class="sub">{esc(preview.chart_id)} · sheet={esc(preview.meta.get('sheet_name', ''))}</div>
  <div class="badges">
    <span class="badge">{esc(preview.chart_type)}</span>
    <span class="badge {status_class}">{esc(status_label)}</span>
    <span class="badge">render={esc(preview.render_mode)}</span>
  </div>
  <div class="meta-grid">
    <div><span>source workbook</span>{esc(preview.meta.get('source_workbook') or '—')}</div>
    <div><span>source sheet</span>{esc(preview.meta.get('source_sheet') or '—')}</div>
    <div><span>processed csv</span>{esc(preview.meta.get('processed_csv') or '—')}</div>
    <div><span>data module</span>{esc(preview.meta.get('data_module_id') or '—')}</div>
  </div>
  {notes_html}
  {chart_html}
  {table_html}
</section>
"""


def _table_markup(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(
        f'<th class="col-{esc(h)}">{esc(h)}</th>' for h in headers
    )
    body_rows = []
    for row in rows:
        cells = []
        for header, value in zip(headers, row):
            cells.append(f'<td class="col-{esc(header)}">{_cell_html(header, value)}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        f'<div class="table-wrap">'
        f'<table class="sample"><thead><tr>{head}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def _render_sample_table(preview: ChartPreviewSpec, *, section_index: int) -> str:
    if preview.site_tabs:
        tab_buttons = []
        panels = []
        for tab_index, tab in enumerate(preview.site_tabs):
            active = " active" if tab_index == 0 else ""
            tab_id = f"site-{section_index}-{tab_index}"
            tab_buttons.append(
                f'<button type="button" class="site-tab{active}" data-target="{tab_id}" '
                f'onclick="window.cmSwitchSiteTab(this)">{esc(tab.site)}</button>'
            )
            panels.append(
                f'<div class="site-panel{active}" id="{tab_id}">'
                f"{_table_markup(tab.headers, tab.rows)}</div>"
            )
        return f"""
<details class="sample-block" open>
  <summary>数据样例（按站点切换，每站最多 {SAMPLE_TABLE_ROWS} 行）</summary>
  <div class="site-tabs">{"".join(tab_buttons)}</div>
  {"".join(panels)}
</details>
"""

    if not preview.sample_headers:
        return ""
    return f"""
<details class="sample-block" open>
  <summary>数据样例（最多 {SAMPLE_TABLE_ROWS} 行）</summary>
  {_table_markup(preview.sample_headers, preview.sample_rows)}
</details>
"""


def _cell_html(header: str, value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if header == "item_image" and text.startswith(("http://", "https://")):
        safe = esc(text)
        return (
            f'<img class="thumb" src="{safe}" alt="item" '
            f'loading="lazy" onerror="this.style.display=\'none\'"/>'
        )
    if header in {"item_link", "shop_link"} and text.startswith(("http://", "https://")):
        safe = esc(text)
        return f'<a href="{safe}" target="_blank" rel="noopener noreferrer">link</a>'
    return esc(text)


def _render_plotly_bootstraps(previews: list[ChartPreviewSpec]) -> str:
    clean = [
        "<script>",
        """
window.cmToggleChartLabels = function(btn) {
  const chartId = btn.getAttribute('data-chart');
  const gd = document.getElementById(chartId);
  if (!gd || !gd.data) return;
  const next = btn.getAttribute('data-on') !== '1';
  btn.setAttribute('data-on', next ? '1' : '0');
  btn.textContent = next ? '隐藏数字' : '显示数字';
  for (let i = 0; i < gd.data.length; i++) {
    const t = gd.data[i] || {};
    if (t.type === 'scatter') {
      Plotly.restyle(gd, {
        mode: next ? 'lines+markers+text' : 'lines+markers',
        textposition: next ? 'top center' : 'top center'
      }, [i]);
    } else if (t.type === 'bar') {
      Plotly.restyle(gd, { textposition: next ? 'auto' : 'none' }, [i]);
    } else if (t.type === 'pie') {
      Plotly.restyle(gd, { textinfo: next ? 'percent+label' : 'none' }, [i]);
    }
  }
};
window.cmSwitchSiteTab = function(btn) {
  const targetId = btn.getAttribute('data-target');
  const wrap = btn.closest('details') || btn.parentElement.parentElement;
  wrap.querySelectorAll('.site-tabs button').forEach((el) => el.classList.remove('active'));
  wrap.querySelectorAll('.site-panel').forEach((el) => el.classList.remove('active'));
  btn.classList.add('active');
  const panel = document.getElementById(targetId);
  if (panel) panel.classList.add('active');
};
""".strip(),
    ]
    for index, preview in enumerate(previews):
        if not preview.plotly_payload:
            continue
        payload = json.dumps(preview.plotly_payload, ensure_ascii=False)
        clean.append(
            "(() => { "
            f"const p = {payload}; "
            f"Plotly.newPlot('chart-{index}', p.data, p.layout, "
            "{responsive:true, displayModeBar:false}); "
            "})();"
        )
    clean.append("</script>")
    return "\n".join(clean)


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)
