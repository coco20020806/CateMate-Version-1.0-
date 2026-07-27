"""Plotly chart builders for HTML report."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from catemate.html_report.schemas import ChartBinding

MAX_TABLE_ROWS = 50
MAX_SERIES = 20


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_trend_figure(df: pd.DataFrame, binding: ChartBinding) -> go.Figure:
    if binding.x_field is None or not binding.y_fields:
        raise ValueError(f"Trend chart requires x_field and y_fields: {binding.chart_id}")

    work = df.copy()
    work[binding.x_field] = work[binding.x_field].astype(str)
    y_field = binding.y_fields[0]
    work[y_field] = _to_numeric(work[y_field])

    fig = go.Figure()
    if binding.series_field and binding.series_field in work.columns:
        series_values = work[binding.series_field].dropna().unique().tolist()[:MAX_SERIES]
        for series_value in series_values:
            subset = work[work[binding.series_field] == series_value].sort_values(binding.x_field)
            fig.add_trace(
                go.Scatter(
                    x=subset[binding.x_field],
                    y=subset[y_field],
                    mode="lines+markers",
                    name=str(series_value),
                )
            )
    else:
        grouped = work.groupby(binding.x_field, dropna=False)[y_field].sum(min_count=1).reset_index()
        grouped = grouped.sort_values(binding.x_field)
        fig.add_trace(
            go.Scatter(
                x=grouped[binding.x_field],
                y=grouped[y_field],
                mode="lines+markers",
                name=y_field,
            )
        )

    fig.update_layout(
        title=binding.title,
        xaxis_title=binding.x_field,
        yaxis_title=y_field,
        template="plotly_white",
        height=420,
    )
    return fig


def build_bar_figure(df: pd.DataFrame, binding: ChartBinding) -> go.Figure:
    if binding.x_field is None or not binding.y_fields:
        raise ValueError(f"Bar chart requires x_field and y_fields: {binding.chart_id}")

    work = df.copy()
    y_field = binding.y_fields[0]
    work[y_field] = _to_numeric(work[y_field])
    grouped = work.groupby(binding.x_field, dropna=False)[y_field].sum(min_count=1).reset_index()
    grouped = grouped.sort_values(y_field, ascending=False)
    if binding.top_n:
        grouped = grouped.head(binding.top_n)

    fig = go.Figure(
        data=[
            go.Bar(
                x=grouped[binding.x_field].astype(str),
                y=grouped[y_field],
                name=y_field,
            )
        ]
    )
    fig.update_layout(
        title=binding.title,
        xaxis_title=binding.x_field,
        yaxis_title=y_field,
        template="plotly_white",
        height=420,
    )
    return fig


def build_share_figure(df: pd.DataFrame, binding: ChartBinding) -> go.Figure:
    y_field = binding.y_fields[0] if binding.y_fields else None
    if y_field is None:
        raise ValueError(f"Share chart requires y_fields: {binding.chart_id}")

    work = df.copy()
    work[y_field] = _to_numeric(work[y_field])
    label_field = binding.x_field or (binding.series_field if binding.series_field in work.columns else None)
    if label_field is None:
        label_field = work.columns[0]

    grouped = work.groupby(label_field, dropna=False)[y_field].sum(min_count=1).reset_index()
    grouped = grouped.sort_values(y_field, ascending=False)
    if binding.top_n:
        grouped = grouped.head(binding.top_n)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=grouped[label_field].astype(str),
                values=grouped[y_field],
                hole=0.3,
            )
        ]
    )
    fig.update_layout(title=binding.title, template="plotly_white", height=420)
    return fig


def build_table_figure(df: pd.DataFrame, binding: ChartBinding) -> go.Figure:
    limit = binding.top_n or MAX_TABLE_ROWS
    sample = df.head(limit).copy()
    sample.columns = [str(c) for c in sample.columns]
    headers = list(sample.columns)
    cells = [sample.iloc[:, index].astype(str).tolist() for index in range(sample.shape[1])]
    fig = go.Figure(
        data=[
            go.Table(
                header=dict(values=headers, fill_color="#f0f0f0", align="left"),
                cells=dict(values=cells, align="left"),
            )
        ]
    )
    fig.update_layout(title=binding.title, height=min(520, 80 + 28 * len(sample)))
    return fig


def build_kpi_row_figure(df: pd.DataFrame, binding: ChartBinding) -> go.Figure:
    if df.empty or not binding.y_fields:
        raise ValueError(f"KPI row requires data and y_fields: {binding.chart_id}")

    row = df.iloc[0]
    fig = go.Figure()
    for index, y_field in enumerate(binding.y_fields[:4]):
        value = _to_numeric(pd.Series([row.get(y_field)])).iloc[0]
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=float(value) if pd.notna(value) else 0,
                title={"text": y_field},
                domain={"row": 0, "column": index},
            )
        )
    fig.update_layout(
        title=binding.title,
        grid={"rows": 1, "columns": min(len(binding.y_fields), 4), "pattern": "independent"},
        height=220,
    )
    return fig


def build_chart_figure(df: pd.DataFrame, binding: ChartBinding) -> go.Figure:
    if df.empty:
        raise ValueError(f"Table {binding.table_id} is empty")

    builders = {
        "trend": build_trend_figure,
        "bar": build_bar_figure,
        "share": build_share_figure,
        "table": build_table_figure,
        "kpi_row": build_kpi_row_figure,
    }
    builder = builders.get(binding.chart_type)
    if builder is None:
        raise ValueError(f"Unsupported chart_type={binding.chart_type}")
    return builder(df, binding)
