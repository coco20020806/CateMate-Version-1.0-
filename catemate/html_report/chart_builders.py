"""Plotly chart builders for HTML report."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go

from catemate.html_report.schemas import ChartBinding

MAX_TABLE_ROWS = 50
MAX_SERIES = 20
MONTHLY_X_FIELDS = {"grass_month", "month", "year_month"}


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _parse_time_value(value: object) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
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


def _format_trend_x(value: object, *, monthly: bool) -> str:
    parsed = _parse_time_value(value)
    if parsed is None:
        return "" if value is None else str(value)
    if monthly:
        return parsed.strftime("%Y-%m")
    return parsed.strftime("%Y-%m-%d")


def _format_metric_label(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{value:,.0f}"
    if abs(value) >= 100:
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def _is_monthly_x_field(field_name: str | None) -> bool:
    if not field_name:
        return False
    return field_name.strip().lower() in MONTHLY_X_FIELDS


def build_trend_figure(df: pd.DataFrame, binding: ChartBinding) -> go.Figure:
    if binding.x_field is None or not binding.y_fields:
        raise ValueError(f"Trend chart requires x_field and y_fields: {binding.chart_id}")

    work = df.copy()
    monthly = _is_monthly_x_field(binding.x_field)
    work["_x_label"] = work[binding.x_field].map(lambda v: _format_trend_x(v, monthly=monthly))
    y_field = binding.y_fields[0]
    work[y_field] = _to_numeric(work[y_field])

    fig = go.Figure()
    category_labels: list[str] = []
    if binding.series_field and binding.series_field in work.columns:
        series_values = work[binding.series_field].dropna().unique().tolist()[:MAX_SERIES]
        for series_value in series_values:
            subset = work[work[binding.series_field] == series_value].copy()
            subset = subset.sort_values(binding.x_field)
            x_vals = subset["_x_label"].tolist()
            y_vals = subset[y_field].tolist()
            for label in x_vals:
                if label and label not in category_labels:
                    category_labels.append(label)
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode="lines+markers",
                    name=str(series_value),
                    text=[_format_metric_label(float(v)) if pd.notna(v) else "" for v in y_vals],
                )
            )
    else:
        grouped = work.groupby("_x_label", dropna=False)[y_field].sum(min_count=1).reset_index()
        grouped = grouped.sort_values("_x_label")
        x_vals = grouped["_x_label"].tolist()
        y_vals = grouped[y_field].tolist()
        category_labels = [label for label in x_vals if label]
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines+markers",
                name=y_field,
                text=[_format_metric_label(float(v)) if pd.notna(v) else "" for v in y_vals],
            )
        )

    fig.update_layout(
        title=binding.title,
        xaxis_title=binding.x_field,
        yaxis_title=y_field,
        template="plotly_white",
        height=420,
    )
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=category_labels)
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

    y_vals = grouped[y_field].tolist()
    fig = go.Figure(
        data=[
            go.Bar(
                x=grouped[binding.x_field].astype(str),
                y=y_vals,
                name=y_field,
                text=[_format_metric_label(float(v)) if pd.notna(v) else "" for v in y_vals],
                textposition="none",
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

    values = grouped[y_field].tolist()
    fig = go.Figure(
        data=[
            go.Pie(
                labels=grouped[label_field].astype(str),
                values=values,
                hole=0.3,
                text=[_format_metric_label(float(v)) if pd.notna(v) else "" for v in values],
                textinfo="none",
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
