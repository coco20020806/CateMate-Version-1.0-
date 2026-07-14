"""Build PPT-ready chart sheet specs from planning charts + processed tables."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from catemate.core.paths import PROJECT_ROOT
from catemate.planning.schemas import PlanningChartProposal, RequirementPlanningSpec
from catemate.ppt_ready.field_utils import (
    MONTH_TIME_FIELDS,
    price_range_sort_key,
    resolve_trend_time_fields,
)
from catemate.ppt_ready.processed_data_reader import (
    get_table_entry,
    get_table_lineage,
    load_processed_table,
)
from catemate.ppt_ready.schemas import PptReadySheetSpec


SITE_FIELDS = ["grass_region", "region", "site"]
MONTH_FIELDS = MONTH_TIME_FIELDS
CATEGORY_FIELDS = [
    "cb_level1_global_be_category",
    "level2_global_be_category",
    "level3_global_be_category",
]
GMV_FIELDS = ["gmv_usd", "gmv", "ADG", "current_adgmv(RAW)"]
ORDER_FIELDS = ["orders", "order", "ADO", "current_ado(RAW)"]
PRICE_FIELDS = ["item_price_usd", "Price_Range_USD"]
YOY_HINTS = ("yoy", "growth", "比例", "proportion")
PROPORTION_HINTS = ("proportion", "share", "rate", "ratio")
TABLE_SORT_FIELDS = [
    "current_adgmv(RAW)",
    "current_ado(RAW)",
    "gmv_usd",
    "orders",
    "ADG",
    "ADO",
]
TABLE_KEEP_FIELDS = [
    "item_name",
    "item_link",
    "item_image",
    "item_price_usd",
    "current_ado(RAW)",
    "current_adgmv(RAW)",
    "grass_region",
    "keyword",
    "shop_id",
    "shop_link",
    "ggp_account_name",
    "user_name",
    *CATEGORY_FIELDS,
]
MAX_TABLE_ROWS = 50
MAX_PARTIAL_ROWS = 50

AOV_NULL_REASON = (
    "aov 为空通常因为 order 字段为 0 或缺失；系统不会计算除以 0 的结果。"
)
SHARE_ZERO_REASON = (
    "share 为空因为 metric 合计为 0 或 NA；系统不会用不为零分母之外的值硬算占比。"
)

MISSING_NOTE_KEYWORDS = (
    "missing",
    "not found",
    "no recognized",
    "no usable",
    "empty",
    "unsupported",
    "zero/na",
    "zero",
    "无法",
    "缺",
    "不支持",
    "failed to load",
    "partial",
)


def dedupe_fields(fields: list[str]) -> list[str]:
    """Preserve order while removing duplicate field names."""
    seen: set[str] = set()
    unique: list[str] = []
    for field in fields:
        if field not in seen:
            seen.add(field)
            unique.append(field)
    return unique


def exclude_dimension_fields(metric_fields: list[str], dim_fields: list[str]) -> list[str]:
    """Drop metrics that are already used as grouping dimensions."""
    dim_set = set(dim_fields)
    return [field for field in metric_fields if field not in dim_set]


def build_ppt_ready_sheets(
    planning_spec: RequirementPlanningSpec,
    manifest: dict[str, Any],
    processed_data_dir: Path,
    project_root: Path | None = None,
) -> tuple[list[PptReadySheetSpec], dict[str, dict[str, Any]]]:
    root = project_root or PROJECT_ROOT
    sheets: list[PptReadySheetSpec] = []
    used_lineage: dict[str, dict[str, Any]] = {}
    used_sheet_names: set[str] = set()
    for index, chart in enumerate(planning_spec.proposed_charts, start=1):
        chart_id = (chart.chart_id or "").strip() or f"chart_{index:02d}"
        sheet = _build_one_sheet(
            chart=chart,
            chart_id=chart_id,
            manifest=manifest,
            processed_data_dir=processed_data_dir,
            planning_spec=planning_spec,
            used_sheet_names=used_sheet_names,
            project_root=root,
            used_lineage=used_lineage,
        )
        sheets.append(sheet)
    return sheets, used_lineage


def _build_one_sheet(
    *,
    chart: PlanningChartProposal,
    chart_id: str,
    manifest: dict[str, Any],
    processed_data_dir: Path,
    planning_spec: RequirementPlanningSpec,
    used_sheet_names: set[str],
    project_root: Path,
    used_lineage: dict[str, dict[str, Any]],
) -> PptReadySheetSpec:
    sheet_name = unique_sheet_name(safe_sheet_name(chart_id), used_sheet_names)
    chart_type = (chart.chart_type or "unknown").strip().lower()
    notes: list[str] = []
    table_ids = list(chart.table_ids or [])

    if chart_type not in {"trend", "share", "bar", "table"}:
        notes.append(f"Unsupported chart_type={chart.chart_type!r} in v1 generic builder.")
        return finalize_sheet(
            PptReadySheetSpec(
                sheet_name=sheet_name,
                chart_id=chart_id,
                chart_title=chart.title,
                chart_type=chart_type or "unknown",
                data_module_id=chart.data_module_id,
                source_table_ids=table_ids,
                rows=[{"note": notes[0]}],
                notes=notes,
                output_status="unsupported",
                source_rule_note=(
                    f"v1 generic builder does not support chart_type={chart.chart_type!r}"
                ),
                missing_data_note="unsupported chart type; no data generated",
                null_reason_note="v1 不支持该 chart_type，因此只有说明行。",
            ),
            used_table_ids=[],
            requested_table_ids=table_ids,
            manifest=manifest,
            processed_data_dir=processed_data_dir,
            project_root=project_root,
            used_lineage=used_lineage,
        )

    if not table_ids:
        notes.append("Chart has no table_ids.")
        return finalize_sheet(
            PptReadySheetSpec(
                sheet_name=sheet_name,
                chart_id=chart_id,
                chart_title=chart.title,
                chart_type=chart_type,
                data_module_id=chart.data_module_id,
                source_table_ids=[],
                rows=[{"note": notes[0]}],
                notes=notes,
                output_status="unsupported",
                source_rule_note="chart has no table_ids",
                missing_data_note="table_id missing; chart.table_ids is empty",
            ),
            used_table_ids=[],
            requested_table_ids=[],
            manifest=manifest,
            processed_data_dir=processed_data_dir,
            project_root=project_root,
            used_lineage=used_lineage,
        )

    multi_table_note = ""
    if len(table_ids) > 1:
        multi_table_note = (
            f"v1 uses first available table only; unused table_ids={table_ids[1:]}"
        )
        notes.append(multi_table_note)

    df, used_table_id, load_notes = _load_first_available_table(
        table_ids, manifest, processed_data_dir
    )
    notes.extend(load_notes)
    if df is None or used_table_id is None:
        missing = summarize_missing_from_notes(notes) or (
            "No usable processed table; table_id not found or CSV missing."
        )
        return finalize_sheet(
            PptReadySheetSpec(
                sheet_name=sheet_name,
                chart_id=chart_id,
                chart_title=chart.title,
                chart_type=chart_type,
                data_module_id=chart.data_module_id,
                source_table_ids=table_ids,
                rows=[{"note": notes[-1] if notes else "No usable processed table."}],
                notes=notes,
                output_status="unsupported",
                source_rule_note=multi_table_note or "failed to load any requested table",
                missing_data_note=missing,
            ),
            used_table_ids=[],
            requested_table_ids=table_ids,
            manifest=manifest,
            processed_data_dir=processed_data_dir,
            project_root=project_root,
            used_lineage=used_lineage,
        )

    df, filter_notes = apply_conservative_category_filter(df, planning_spec)
    notes.extend(filter_notes)

    if chart_type == "trend":
        spec = _build_trend_sheet(sheet_name, chart_id, chart, used_table_id, df, notes)
    elif chart_type == "share":
        spec = _build_share_sheet(sheet_name, chart_id, chart, used_table_id, df, notes)
    elif chart_type == "bar":
        spec = _build_bar_sheet(sheet_name, chart_id, chart, used_table_id, df, notes)
    else:
        spec = _build_table_sheet(sheet_name, chart_id, chart, used_table_id, df, notes)

    if multi_table_note and multi_table_note not in (spec.source_rule_note or ""):
        if spec.source_rule_note:
            spec.source_rule_note = f"{spec.source_rule_note}; {multi_table_note}"
        else:
            spec.source_rule_note = multi_table_note

    return finalize_sheet(
        spec,
        used_table_ids=[used_table_id],
        requested_table_ids=table_ids,
        manifest=manifest,
        processed_data_dir=processed_data_dir,
        project_root=project_root,
        used_lineage=used_lineage,
    )


def finalize_sheet(
    spec: PptReadySheetSpec,
    *,
    used_table_ids: list[str],
    requested_table_ids: list[str],
    manifest: dict[str, Any],
    processed_data_dir: Path,
    project_root: Path,
    used_lineage: dict[str, dict[str, Any]],
) -> PptReadySheetSpec:
    workbook_names: list[str] = []
    source_sheets: list[str] = []
    csv_paths: list[str] = []

    lineage_ids = used_table_ids or []
    # Still record lineage attempts for not-found requested tables (for data_notes).
    for table_id in requested_table_ids:
        lineage = get_table_lineage(
            manifest, table_id, processed_data_dir, project_root=project_root
        )
        used_lineage.setdefault(table_id, lineage)

    for table_id in lineage_ids:
        lineage = get_table_lineage(
            manifest, table_id, processed_data_dir, project_root=project_root
        )
        used_lineage[table_id] = lineage
        if lineage.get("source_workbook_name"):
            workbook_names.append(str(lineage["source_workbook_name"]))
        if lineage.get("source_sheet"):
            source_sheets.append(str(lineage["source_sheet"]))
        if lineage.get("processed_csv_path"):
            csv_paths.append(str(lineage["processed_csv_path"]))

    spec.source_workbook_names = workbook_names
    spec.source_sheets = source_sheets
    spec.processed_csv_paths = csv_paths

    if not spec.missing_data_note:
        spec.missing_data_note = summarize_missing_from_notes(spec.notes)
    if not spec.null_reason_note:
        spec.null_reason_note = summarize_null_reason_from_notes(spec.notes, spec.rows)
    return spec


def summarize_missing_from_notes(notes: list[str]) -> str:
    hits: list[str] = []
    for note in notes:
        lowered = note.lower()
        if any(keyword in lowered for keyword in MISSING_NOTE_KEYWORDS):
            hits.append(note)
    return " | ".join(hits)


def summarize_null_reason_from_notes(notes: list[str], rows: list[dict[str, Any]]) -> str:
    reasons: list[str] = []
    joined = " ".join(notes).lower()
    if "computed aov" in joined or any("aov" in (note.lower()) for note in notes):
        reasons.append(AOV_NULL_REASON)
    if "share total is zero" in joined:
        reasons.append(SHARE_ZERO_REASON)
    if any("unsupported chart_type" in note.lower() for note in notes):
        reasons.append("v1 不支持该 chart_type，因此只有说明行。")

    # Evidence-based: output rows contain empty values for known computed fields.
    if rows and "aov" in rows[0] and AOV_NULL_REASON not in reasons:
        if any(row.get("aov") in (None, "") for row in rows):
            reasons.append(AOV_NULL_REASON)
    if rows and "share" in rows[0] and SHARE_ZERO_REASON not in reasons:
        if any(row.get("share") in (None, "") for row in rows) and "share total is zero" in joined:
            reasons.append(SHARE_ZERO_REASON)
    return " | ".join(reasons)


def _load_first_available_table(
    table_ids: list[str],
    manifest: dict[str, Any],
    processed_data_dir: Path,
) -> tuple[pd.DataFrame | None, str | None, list[str]]:
    notes: list[str] = []
    for table_id in table_ids:
        entry = get_table_entry(manifest, table_id)
        if entry is None:
            notes.append(f"table_id not found in processed manifest: {table_id}")
            continue
        try:
            df = load_processed_table(entry, processed_data_dir=processed_data_dir)
        except Exception as exc:
            notes.append(f"Failed to load table {table_id}: {exc}")
            continue
        if df.empty:
            notes.append(f"Processed table is empty: {table_id}")
            continue
        return df, table_id, notes
    if not notes:
        notes.append("No usable processed table for chart.")
    return None, None, notes


def apply_conservative_category_filter(
    df: pd.DataFrame,
    planning_spec: RequirementPlanningSpec,
) -> tuple[pd.DataFrame, list[str]]:
    """Exact-match filter only; never fuzzy-map frontend paths to global categories."""
    notes: list[str] = []
    if not planning_spec.target_categories:
        notes.append("No target_categories in planning spec; no category filter applied.")
        return df, notes

    candidates: list[str] = []
    for item in planning_spec.target_categories:
        path = (item.path or "").strip()
        if not path:
            continue
        if ">" in path or "/" in path:
            notes.append(
                f"Skipped unreliable frontend/path category mapping for: {path}"
            )
            continue
        candidates.append(path)

    if not candidates:
        notes.append("No exact-matchable target categories; no category filter applied.")
        return df, notes

    category_cols = [col for col in CATEGORY_FIELDS if col in df.columns]
    if not category_cols:
        notes.append("No category columns in table; no category filter applied.")
        return df, notes

    mask = pd.Series(False, index=df.index)
    matched_any = False
    for value in candidates:
        value_mask = pd.Series(False, index=df.index)
        for col in category_cols:
            value_mask = value_mask | (df[col].astype(str).str.strip() == value)
        if value_mask.any():
            matched_any = True
            mask = mask | value_mask

    if not matched_any:
        notes.append(
            f"target_categories {candidates} not found as exact values in category columns; "
            "no category filter applied."
        )
        return df, notes

    filtered = df.loc[mask].copy()
    notes.append(
        f"Applied exact category filter for {candidates}; "
        f"rows {len(df)} -> {len(filtered)}."
    )
    return filtered, notes


def _build_trend_sheet(
    sheet_name: str,
    chart_id: str,
    chart: PlanningChartProposal,
    table_id: str,
    df: pd.DataFrame,
    notes: list[str],
) -> PptReadySheetSpec:
    time_candidates, is_daily, daily_note = resolve_trend_time_fields(
        table_ids=[table_id],
        chart_id=chart_id,
        chart_title=chart.title,
        grain=chart.grain,
        preferred_from_chart=list(chart.dimensions),
    )
    time_field = first_existing(df, time_candidates)
    if is_daily:
        rule = f"使用 table_id={table_id}，按 chart_type=trend 按维度+日(grass_date)聚合输出"
        if daily_note:
            notes.append(daily_note)
        # Keep grass_date; drop month-only dims that would collapse daily grain.
        skip_dims = {"month", "year"} if time_field == "grass_date" else set()
    else:
        rule = f"使用 table_id={table_id}，按 chart_type=trend 按维度+月份聚合输出"
        skip_dims = set()

    site_field = first_existing(df, SITE_FIELDS)
    category_fields = [c for c in CATEGORY_FIELDS if c in df.columns]

    if time_field is None:
        notes.append("Missing month/date field for trend chart; outputting partial sample rows.")
        rows = dataframe_to_rows(
            df.head(MAX_PARTIAL_ROWS), preferred_columns=_preferred_columns(df, chart)
        )
        return PptReadySheetSpec(
            sheet_name=sheet_name,
            chart_id=chart_id,
            chart_title=chart.title,
            chart_type="trend",
            data_module_id=chart.data_module_id,
            source_table_ids=[table_id],
            rows=rows or [{"note": "No rows available after load."}],
            notes=notes,
            output_status="partial",
            source_rule_note=rule,
            missing_data_note="month field missing" if not is_daily else "date field missing",
        )

    group_cols = []
    if site_field:
        group_cols.append(site_field)
    group_cols.extend(category_fields)
    group_cols.append(time_field)
    for dim in chart.dimensions:
        if dim in skip_dims:
            continue
        if dim in df.columns and dim not in group_cols:
            group_cols.append(dim)
    group_cols = dedupe_fields(group_cols)
    metric_fields = exclude_dimension_fields(resolve_metric_fields(df, chart.metrics), group_cols)

    if not metric_fields:
        notes.append("No recognized metric fields for trend; outputting partial sample rows.")
        rows = dataframe_to_rows(df.head(MAX_PARTIAL_ROWS), preferred_columns=group_cols)
        return PptReadySheetSpec(
            sheet_name=sheet_name,
            chart_id=chart_id,
            chart_title=chart.title,
            chart_type="trend",
            data_module_id=chart.data_module_id,
            source_table_ids=[table_id],
            rows=rows or [{"note": "No metric fields found."}],
            notes=notes,
            output_status="partial",
            source_rule_note=rule,
            missing_data_note="metric missing",
        )

    work = df.copy()
    for col in metric_fields:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    grouped = work.groupby(group_cols, dropna=False)[metric_fields].sum(min_count=1).reset_index()
    # Keep time order readable for daily data.
    if time_field in grouped.columns:
        grouped = grouped.sort_values(by=[c for c in [site_field, time_field] if c], kind="mergesort")
    gmv_field, order_field = resolve_aov_fields(grouped)
    null_reason = ""
    if gmv_field and order_field:
        grouped["aov"] = grouped.apply(
            lambda row: (row[gmv_field] / row[order_field])
            if pd.notna(row[order_field]) and row[order_field] not in (0, 0.0)
            else pd.NA,
            axis=1,
        )
        notes.append(f"Computed aov = {gmv_field} / {order_field}.")
        null_reason = AOV_NULL_REASON

    status = "generated" if not notes else "partial"
    if all(
        n.startswith("v1 uses first")
        or n.startswith("Applied exact category filter")
        or n.startswith("Computed aov")
        or n.startswith("No target_categories")
        or n.startswith("No exact-matchable")
        or n.startswith("Skipped unreliable")
        or n.startswith("target_categories")
        or n.startswith("No category columns")
        or n.startswith("daily data preview uses grass_date")
        for n in notes
    ):
        status = "generated"

    rows = dataframe_to_rows(grouped)
    return PptReadySheetSpec(
        sheet_name=sheet_name,
        chart_id=chart_id,
        chart_title=chart.title,
        chart_type="trend",
        data_module_id=chart.data_module_id,
        source_table_ids=[table_id],
        rows=rows or [{"note": "Aggregated frame was empty."}],
        notes=notes,
        output_status=status if rows else "empty",
        source_rule_note=rule,
        null_reason_note=null_reason,
        missing_data_note="" if rows else "empty aggregation result",
    )


def _build_share_sheet(
    sheet_name: str,
    chart_id: str,
    chart: PlanningChartProposal,
    table_id: str,
    df: pd.DataFrame,
    notes: list[str],
) -> PptReadySheetSpec:
    rule = f"使用 table_id={table_id}，按 chart_type=share 聚合并计算/复制 share"
    dim_fields = dedupe_fields([d for d in chart.dimensions if d in df.columns])
    if not dim_fields:
        dim_fields = dedupe_fields([c for c in SITE_FIELDS + CATEGORY_FIELDS + PRICE_FIELDS if c in df.columns])

    metric_field = resolve_share_metric(df, chart.metrics)
    if metric_field in dim_fields:
        metric_field = resolve_share_metric(
            df,
            [name for name in chart.metrics if name not in dim_fields],
        )
    if metric_field in dim_fields:
        metric_field = None

    if metric_field is None or not dim_fields:
        notes.append(
            "Missing metric or dimensions for share chart; outputting partial sample rows."
        )
        rows = dataframe_to_rows(
            df.head(MAX_PARTIAL_ROWS), preferred_columns=_preferred_columns(df, chart)
        )
        missing_parts = []
        if metric_field is None:
            missing_parts.append("metric missing")
        if not dim_fields:
            missing_parts.append("dimensions missing")
        return PptReadySheetSpec(
            sheet_name=sheet_name,
            chart_id=chart_id,
            chart_title=chart.title,
            chart_type="share",
            data_module_id=chart.data_module_id,
            source_table_ids=[table_id],
            rows=rows or [{"note": "Unable to compute share."}],
            notes=notes,
            output_status="partial",
            source_rule_note=rule,
            missing_data_note="; ".join(missing_parts),
        )

    work = df.copy()
    work[metric_field] = pd.to_numeric(work[metric_field], errors="coerce")
    grouped = work.groupby(dim_fields, dropna=False)[metric_field].sum(min_count=1).reset_index()
    null_reason = ""
    if is_proportion_field(metric_field):
        grouped["share"] = grouped[metric_field]
        status = "generated"
        notes.append(
            f"metric={metric_field} appears to be an existing proportion/share field; "
            "copied to share without recomputing."
        )
    else:
        total = grouped[metric_field].sum(min_count=1)
        if pd.isna(total) or total == 0:
            notes.append("Share total is zero/NA; share column left empty.")
            grouped["share"] = pd.NA
            status = "partial"
            null_reason = SHARE_ZERO_REASON
        else:
            grouped["share"] = grouped[metric_field] / total
            status = "generated"
            notes.append(
                f"share computed from metric={metric_field} over dimensions={dim_fields}."
            )

    rows = dataframe_to_rows(grouped)
    status = status if rows else "empty"
    # Price tier sheets: keep natural price order in workbook output.
    if "Price_Range_USD" in grouped.columns:
        grouped = grouped.copy()
        grouped["_price_sort"] = grouped["Price_Range_USD"].map(price_range_sort_key)
        grouped = grouped.sort_values(by="_price_sort", kind="mergesort").drop(columns=["_price_sort"])
        rows = dataframe_to_rows(grouped)
        notes.append("Sorted by Price_Range_USD natural order (not by metric desc).")

    return PptReadySheetSpec(
        sheet_name=sheet_name,
        chart_id=chart_id,
        chart_title=chart.title,
        chart_type="share",
        data_module_id=chart.data_module_id,
        source_table_ids=[table_id],
        rows=rows or [{"note": "Share aggregation empty."}],
        notes=notes,
        output_status=status,
        source_rule_note=rule,
        null_reason_note=null_reason,
        missing_data_note="" if rows else "empty aggregation result",
    )


def _build_bar_sheet(
    sheet_name: str,
    chart_id: str,
    chart: PlanningChartProposal,
    table_id: str,
    df: pd.DataFrame,
    notes: list[str],
) -> PptReadySheetSpec:
    rule = f"使用 table_id={table_id}，按 chart_type=bar 聚合输出"
    dim_fields = dedupe_fields([d for d in chart.dimensions if d in df.columns])
    if not dim_fields:
        dim_fields = dedupe_fields([c for c in SITE_FIELDS + CATEGORY_FIELDS + PRICE_FIELDS if c in df.columns])

    metric_fields = [m for m in chart.metrics if m in df.columns]
    if not metric_fields:
        metric_fields = resolve_metric_fields(df, chart.metrics)
    metric_fields = exclude_dimension_fields(dedupe_fields(metric_fields), dim_fields)

    yoy_fields = [
        col
        for col in df.columns
        if any(hint in str(col).lower() for hint in YOY_HINTS)
        and col not in metric_fields
    ]

    if not dim_fields or not metric_fields:
        notes.append("Missing dimensions or metrics for bar chart; outputting partial sample rows.")
        rows = dataframe_to_rows(
            df.head(MAX_PARTIAL_ROWS), preferred_columns=_preferred_columns(df, chart)
        )
        missing_parts = []
        if not dim_fields:
            missing_parts.append("dimensions missing")
        if not metric_fields:
            missing_parts.append("metric missing")
        return PptReadySheetSpec(
            sheet_name=sheet_name,
            chart_id=chart_id,
            chart_title=chart.title,
            chart_type="bar",
            data_module_id=chart.data_module_id,
            source_table_ids=[table_id],
            rows=rows or [{"note": "Unable to aggregate bar data."}],
            notes=notes,
            output_status="partial",
            source_rule_note=rule,
            missing_data_note="; ".join(missing_parts),
        )

    work = df.copy()
    for col in metric_fields + yoy_fields:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    agg_fields = exclude_dimension_fields(
        dedupe_fields(metric_fields + [c for c in yoy_fields if c in work.columns]),
        dim_fields,
    )

    if not dim_fields or not agg_fields:
        notes.append("Missing dimensions or metrics for bar chart; outputting partial sample rows.")
        rows = dataframe_to_rows(
            df.head(MAX_PARTIAL_ROWS), preferred_columns=_preferred_columns(df, chart)
        )
        missing_parts = []
        if not dim_fields:
            missing_parts.append("dimensions missing")
        if not agg_fields:
            missing_parts.append("metric missing")
        return PptReadySheetSpec(
            sheet_name=sheet_name,
            chart_id=chart_id,
            chart_title=chart.title,
            chart_type="bar",
            data_module_id=chart.data_module_id,
            source_table_ids=[table_id],
            rows=rows or [{"note": "Unable to aggregate bar data."}],
            notes=notes,
            output_status="partial",
            source_rule_note=rule,
            missing_data_note="; ".join(missing_parts),
        )

    grouped = work.groupby(dim_fields, dropna=False)[agg_fields].sum(min_count=1).reset_index()

    null_reason = ""
    gmv_field, order_field = resolve_aov_fields(grouped)
    if gmv_field and order_field:
        grouped["aov"] = grouped.apply(
            lambda row: (row[gmv_field] / row[order_field])
            if pd.notna(row[order_field]) and row[order_field] not in (0, 0.0)
            else pd.NA,
            axis=1,
        )
        notes.append(f"Computed aov = {gmv_field} / {order_field}.")
        null_reason = AOV_NULL_REASON
    if yoy_fields:
        notes.append(f"Preserved existing growth/yoy-like fields: {yoy_fields}.")
    else:
        notes.append("No yoy/growth fields found; YoY not invented.")
    if metric_fields != list(chart.metrics):
        notes.append(
            "Skipped metric fields that overlap grouping dimensions "
            f"(dimensions={dim_fields}, metrics={chart.metrics})."
        )

    rows = dataframe_to_rows(grouped)
    status = "generated" if rows else "empty"
    if "Price_Range_USD" in grouped.columns:
        grouped = grouped.copy()
        grouped["_price_sort"] = grouped["Price_Range_USD"].map(price_range_sort_key)
        grouped = grouped.sort_values(by="_price_sort", kind="mergesort").drop(columns=["_price_sort"])
        rows = dataframe_to_rows(grouped)
        notes.append("Sorted by Price_Range_USD natural order (not by metric desc).")
    return PptReadySheetSpec(
        sheet_name=sheet_name,
        chart_id=chart_id,
        chart_title=chart.title,
        chart_type="bar",
        data_module_id=chart.data_module_id,
        source_table_ids=[table_id],
        rows=rows or [{"note": "Bar aggregation empty."}],
        notes=notes,
        output_status=status,
        source_rule_note=rule,
        null_reason_note=null_reason,
        missing_data_note="" if rows else "empty aggregation result",
    )


def _build_table_sheet(
    sheet_name: str,
    chart_id: str,
    chart: PlanningChartProposal,
    table_id: str,
    df: pd.DataFrame,
    notes: list[str],
) -> PptReadySheetSpec:
    work = df.copy()
    sort_field = first_existing(work, TABLE_SORT_FIELDS + list(chart.metrics))
    if sort_field:
        work[sort_field] = pd.to_numeric(work[sort_field], errors="coerce")
        work = work.sort_values(by=sort_field, ascending=False, na_position="last")
        notes.append(
            f"Sorted by {sort_field} descending; limited to top {MAX_TABLE_ROWS} rows."
        )
        rule = (
            f"table 类型按 {sort_field} 降序取 Top {MAX_TABLE_ROWS}；"
            f"使用 table_id={table_id}"
        )
    else:
        rule = f"table 类型输出前 {MAX_TABLE_ROWS} 行；使用 table_id={table_id}"
        notes.append(f"No sort field found; limited to first {MAX_TABLE_ROWS} rows.")

    keep = []
    for col in TABLE_KEEP_FIELDS + list(chart.dimensions) + list(chart.metrics):
        if col in work.columns and col not in keep:
            keep.append(col)
    missing_note = ""
    if not keep:
        keep = list(work.columns[:20])
        notes.append("Preferred table fields missing; kept first available columns.")
        missing_note = "preferred table fields missing; used first available columns"

    # Evidence: count nulls in kept columns without inventing reasons beyond field presence.
    sample = work[keep].head(MAX_TABLE_ROWS)
    null_bits: list[str] = []
    for col in keep:
        null_count = int(sample[col].isna().sum()) if col in sample.columns else 0
        if null_count > 0:
            null_bits.append(
                f"字段 {col} 存在于 processed table，但本输出 Top 样本中有 {null_count} 行空值；"
                "请回溯 source_workbook/source_sheet 检查源数据。"
            )
    null_reason = " | ".join(null_bits[:5])

    rows = dataframe_to_rows(sample)
    status = "generated" if rows else "empty"
    return PptReadySheetSpec(
        sheet_name=sheet_name,
        chart_id=chart_id,
        chart_title=chart.title,
        chart_type="table",
        data_module_id=chart.data_module_id,
        source_table_ids=[table_id],
        rows=rows or [{"note": "No table rows available."}],
        notes=notes,
        output_status=status,
        source_rule_note=rule,
        missing_data_note=missing_note if rows else "empty table result",
        null_reason_note=null_reason,
    )


def resolve_metric_fields(df: pd.DataFrame, requested: list[str]) -> list[str]:
    fields: list[str] = []
    for name in requested:
        if name in df.columns and name not in fields:
            fields.append(name)
    for name in GMV_FIELDS + ORDER_FIELDS:
        if name in df.columns and name not in fields:
            fields.append(name)
    return fields


def resolve_share_metric(df: pd.DataFrame, requested: list[str]) -> str | None:
    for name in requested:
        if name in df.columns:
            return name
    for name in GMV_FIELDS + ORDER_FIELDS:
        if name in df.columns:
            return name
    return None


def resolve_aov_fields(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Only compute AOV from explicit GMV and order fields, not ADG/ADO proxies."""
    gmv_field = first_existing(df, ["gmv_usd", "gmv"])
    order_field = first_existing(df, ["orders", "order"])
    return gmv_field, order_field


def is_proportion_field(field_name: str) -> bool:
    normalized = field_name.lower()
    return any(hint in normalized for hint in PROPORTION_HINTS)


def first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _preferred_columns(df: pd.DataFrame, chart: PlanningChartProposal) -> list[str]:
    preferred: list[str] = []
    for name in list(chart.dimensions) + list(chart.metrics) + SITE_FIELDS + MONTH_FIELDS + CATEGORY_FIELDS:
        if name in df.columns and name not in preferred:
            preferred.append(name)
    if not preferred:
        preferred = list(df.columns[:15])
    return preferred


def dataframe_to_rows(
    df: pd.DataFrame,
    preferred_columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    if preferred_columns:
        cols = [c for c in preferred_columns if c in df.columns]
        if cols:
            df = df.loc[:, cols]
    if df.empty:
        return []
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    cleaned: list[dict[str, Any]] = []
    for record in records:
        cleaned.append({str(k): _jsonish(v) for k, v in record.items()})
    return cleaned


def _jsonish(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if pd.isna(value):
        return None
    try:
        if hasattr(value, "item"):
            return value.item()
    except Exception:
        pass
    return str(value)


def safe_sheet_name(name: str) -> str:
    cleaned = re.sub(r"[\\/*?:\[\]]", "_", name.strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = cleaned or "chart"
    return cleaned[:31]


def unique_sheet_name(base: str, used: set[str]) -> str:
    candidate = base[:31]
    if candidate not in used:
        used.add(candidate)
        return candidate
    for index in range(2, 1000):
        suffix = f"_{index}"
        trimmed = base[: max(1, 31 - len(suffix))] + suffix
        if trimmed not in used:
            used.add(trimmed)
            return trimmed
    raise RuntimeError("Unable to allocate unique sheet name")
