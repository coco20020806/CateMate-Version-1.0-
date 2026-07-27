"""Build compact workbook digest for conclusion brief LLM input."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from catemate.orchestration.schemas import AnalysisPlan, ReportBlueprint, SolveVerdict
from catemate.ppt_ready.build_from_data_workbook import read_data_workbook_tables


TIME_COLUMNS = {"grass_month", "month", "year_month", "grass_date", "date"}
RANK_HINTS = {"rank", "item_name", "item_link", "shop_id", "keyword"}
SHARE_HINTS = ("_pct", "share", "proportion", "rate", "ratio")


@dataclass
class WorkbookDigestContext:
    original_question: str
    blueprint: ReportBlueprint | None = None
    plan: AnalysisPlan | None = None
    verdict: SolveVerdict | None = None
    tables: list[dict[str, Any]] = field(default_factory=list)
    table_section_map: dict[str, str] = field(default_factory=dict)
    truncated_tables: list[str] = field(default_factory=list)


def load_json_model(path: Path | None, model_cls: type):
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return model_cls.model_validate(payload)


def build_table_section_map(plan: AnalysisPlan | None) -> dict[str, str]:
    if plan is None:
        return {}
    mapping: dict[str, str] = {}
    for run in plan.runs:
        if run.table_id:
            mapping[run.table_id] = run.section_id
        if run.run_id:
            mapping[run.run_id] = run.section_id
    return mapping


def _column_names_lower(df: pd.DataFrame) -> set[str]:
    return {str(col).strip().lower() for col in df.columns}


def _is_trend_table(columns: set[str]) -> bool:
    return bool(columns & TIME_COLUMNS)


def _is_rank_table(columns: set[str]) -> bool:
    return "rank" in columns or ("item_name" in columns and "orders" in columns)


def _is_share_table(columns: set[str]) -> bool:
    return any(hint in col for col in columns for hint in SHARE_HINTS)


def _format_cell(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return value


def _records_from_df(df: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in df.head(limit).itertuples(index=False, name=None):
        row = {str(df.columns[i]): _format_cell(record[i]) for i in range(len(df.columns))}
        rows.append(row)
    return rows


def _trend_digest(df: pd.DataFrame, *, max_rows: int) -> dict[str, Any]:
    columns = _column_names_lower(df)
    time_col = next((c for c in df.columns if str(c).strip().lower() in TIME_COLUMNS), None)
    metric_cols = [
        c
        for c in df.columns
        if str(c).strip().lower() not in TIME_COLUMNS
        and str(c).strip().lower() not in {"grass_region", "region", "site"}
        and "_mom_pct" not in str(c).strip().lower()
        and "_pct" not in str(c).strip().lower()
    ]
    mom_cols = [c for c in df.columns if "_mom_pct" in str(c).strip().lower()]

    digest: dict[str, Any] = {"table_kind": "trend"}
    if time_col is not None:
        sorted_df = df.sort_values(by=time_col)
        recent = sorted_df.tail(3)
        digest["recent_periods"] = _records_from_df(recent, max_rows)
        if mom_cols:
            latest = sorted_df.tail(1)
            digest["latest_mom"] = _records_from_df(latest, 1)
        for metric in metric_cols[:3]:
            series = pd.to_numeric(sorted_df[metric], errors="coerce").dropna()
            if not series.empty:
                digest.setdefault("metric_range", {})[str(metric)] = {
                    "min": float(series.min()),
                    "max": float(series.max()),
                }
    else:
        digest["sample_rows"] = _records_from_df(df, max_rows)
    return digest


def _rank_digest(df: pd.DataFrame, *, max_rows: int) -> dict[str, Any]:
    columns = _column_names_lower(df)
    working = df
    if "rank" in columns:
        working = df.sort_values(by="rank")
    return {
        "table_kind": "ranked",
        "top_rows": _records_from_df(working, min(5, max_rows)),
    }


def _share_digest(df: pd.DataFrame, *, max_rows: int) -> dict[str, Any]:
    share_col = None
    for col in df.columns:
        lower = str(col).strip().lower()
        if any(hint in lower for hint in SHARE_HINTS):
            share_col = col
            break
    working = df
    if share_col is not None:
        working = df.sort_values(by=share_col, ascending=False)
    return {
        "table_kind": "share",
        "top_segments": _records_from_df(working, min(5, max_rows)),
    }


def digest_table(
    table_id: str,
    df: pd.DataFrame,
    *,
    section_id: str = "",
    max_rows: int = 10,
) -> dict[str, Any]:
    columns = _column_names_lower(df)
    if _is_trend_table(columns):
        kind_payload = _trend_digest(df, max_rows=max_rows)
    elif _is_rank_table(columns):
        kind_payload = _rank_digest(df, max_rows=max_rows)
    elif _is_share_table(columns):
        kind_payload = _share_digest(df, max_rows=max_rows)
    else:
        kind_payload = {
            "table_kind": "generic",
            "sample_rows": _records_from_df(df, max_rows),
        }

    return {
        "table_id": table_id,
        "section_id": section_id,
        "row_count": len(df),
        "columns": [str(c) for c in df.columns],
        **kind_payload,
    }


def build_workbook_digest(
    *,
    workbook_path: Path,
    original_question: str,
    blueprint_path: Path | None = None,
    plan_path: Path | None = None,
    verdict_path: Path | None = None,
    max_tables: int = 30,
    max_rows_per_table: int = 10,
) -> WorkbookDigestContext:
    tables_raw = read_data_workbook_tables(workbook_path)
    if not tables_raw:
        raise ValueError(f"No Data.* sheets found in {workbook_path}")

    blueprint = load_json_model(blueprint_path, ReportBlueprint)
    plan = load_json_model(plan_path, AnalysisPlan)
    verdict = load_json_model(verdict_path, SolveVerdict)
    section_map = build_table_section_map(plan)

    table_items = list(tables_raw.items())
    truncated: list[str] = []
    if len(table_items) > max_tables:
        truncated = [tid for tid, _ in table_items[max_tables:]]
        table_items = table_items[:max_tables]

    digests: list[dict[str, Any]] = []
    for table_id, df in table_items:
        section_id = section_map.get(table_id, "")
        digests.append(
            digest_table(
                table_id,
                df,
                section_id=section_id,
                max_rows=max_rows_per_table,
            )
        )

    return WorkbookDigestContext(
        original_question=original_question,
        blueprint=blueprint,
        plan=plan,
        verdict=verdict,
        tables=digests,
        table_section_map=section_map,
        truncated_tables=truncated,
    )


def digest_to_payload(ctx: WorkbookDigestContext) -> dict[str, Any]:
    blueprint_payload: dict[str, Any] | None = None
    if ctx.blueprint is not None:
        blueprint_payload = {
            "goal": ctx.blueprint.goal,
            "sections": [
                {
                    "section_id": s.section_id,
                    "title": s.title,
                    "sub_question": s.sub_question,
                    "presentation": s.expected_shape.presentation,
                    "metrics": s.expected_shape.metrics,
                }
                for s in ctx.blueprint.sections
            ],
        }

    plan_payload: list[dict[str, Any]] = []
    if ctx.plan is not None:
        for run in ctx.plan.runs:
            if run.status not in {"executed", "failed", "executable", "skipped"}:
                continue
            plan_payload.append(
                {
                    "run_id": run.run_id,
                    "section_id": run.section_id,
                    "module_id": run.module_id,
                    "metric_id": run.metric_id,
                    "table_id": run.table_id,
                    "status": run.status,
                    "scope_label": run.scope_label,
                    "missing": run.missing,
                }
            )

    verdict_payload: dict[str, Any] | None = None
    if ctx.verdict is not None:
        verdict_payload = {
            "verdict": ctx.verdict.verdict,
            "exit_reason": ctx.verdict.exit_reason,
            "solved_sections": ctx.verdict.solved_sections,
            "unsolved_sections": [
                {
                    "section_id": u.section_id,
                    "reason": u.reason,
                    "suggestion": u.suggestion,
                }
                for u in ctx.verdict.unsolved_sections
            ],
            "notes": ctx.verdict.notes,
        }

    return {
        "original_question": ctx.original_question,
        "report_blueprint": blueprint_payload,
        "analysis_plan_runs": plan_payload,
        "solve_verdict": verdict_payload,
        "workbook_digest": {
            "tables": ctx.tables,
            "truncated_tables": ctx.truncated_tables,
            "table_section_map": ctx.table_section_map,
        },
    }
