"""Pure HTML/CSS chart snippets for print report (no Plotly)."""

from __future__ import annotations

import html

from catemate.print_report.schemas import CssChart


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_css_chart(chart: CssChart) -> str:
    if chart.kind == "none" or not chart.series:
        return ""
    title = f'<div class="chart-title" contenteditable="true">{esc(chart.title)}</div>' if chart.title else ""
    caption = (
        f'<div class="chart-caption" contenteditable="true">{esc(chart.caption)}</div>'
        if chart.caption
        else ""
    )
    if chart.kind == "trend_svg":
        return _trend_svg(chart, title, caption)
    if chart.kind == "column":
        return _column(chart, title, caption)
    return _hbar(chart, title, caption)


def _hbar(chart: CssChart, title: str, caption: str) -> str:
    rows = []
    for item in chart.series:
        width = max(0.0, min(100.0, item.relative))
        rows.append(
            "<div class='bar-row' contenteditable='false'>"
            f"<div class='bar-label' contenteditable='true'>{esc(item.label)}</div>"
            "<div class='bar-track'>"
            f"<div class='bar-fill' style='width:{width}%'></div>"
            "</div>"
            f"<div class='bar-display' contenteditable='true'>{esc(item.display)}</div>"
            "</div>"
        )
    return (
        f"<div class='css-chart' contenteditable='false'>{title}"
        f"<div class='bar-list'>{''.join(rows)}</div>{caption}</div>"
    )


def _column(chart: CssChart, title: str, caption: str) -> str:
    cols = []
    for item in chart.series:
        height = max(0.0, min(100.0, item.relative))
        cols.append(
            "<div class='col-item' contenteditable='false'>"
            f"<div class='col-display' contenteditable='true'>{esc(item.display)}</div>"
            "<div class='col-track'>"
            f"<div class='col-fill' style='height:{height}%'></div>"
            "</div>"
            f"<div class='col-label' contenteditable='true'>{esc(item.label)}</div>"
            "</div>"
        )
    return (
        f"<div class='css-chart' contenteditable='false'>{title}"
        f"<div class='col-list'>{''.join(cols)}</div>{caption}</div>"
    )


def _trend_svg(chart: CssChart, title: str, caption: str) -> str:
    if len(chart.series) < 2:
        return _hbar(chart, title, caption)
    n = len(chart.series)
    points = []
    for index, item in enumerate(chart.series):
        x = 40 + index * (520 / max(n - 1, 1))
        y = 160 - max(0.0, min(100.0, item.relative)) * 1.2
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)
    labels = []
    for index, item in enumerate(chart.series):
        x = 40 + index * (520 / max(n - 1, 1))
        labels.append(
            f"<text x='{x:.1f}' y='185' text-anchor='middle' class='svg-label'>{esc(item.label)}</text>"
        )
    return (
        f"<div class='css-chart' contenteditable='false'>{title}"
        "<svg viewBox='0 0 600 200' class='trend-svg' contenteditable='false'>"
        "<polyline fill='none' stroke='var(--brand)' stroke-width='3' "
        f"points='{polyline}'/>"
        f"{''.join(labels)}"
        f"</svg>{caption}</div>"
    )
