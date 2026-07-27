"""Execute comparison PlanRuns using prior subset and parent tables."""

from __future__ import annotations

import pandas as pd

from catemate.execution.result_collector import ExecutionResult
from catemate.orchestration.comparison_compute import compute_subset_l3_share
from catemate.orchestration.schemas import AnalysisPlan, PlanRun
from data_modules.monthly_market_trend.compute import METRIC_SPECS

_PRIMARY_TABLE_BY_METRIC = {
    metric_id: str(spec["table_id"])
    for metric_id, spec in METRIC_SPECS.items()
}


def run_comparison_tables(
    run: PlanRun,
    plan: AnalysisPlan,
    execution: ExecutionResult,
) -> list[tuple[str, pd.DataFrame, str]]:
    metric_id = run.metric_id
    subset_df, parent_df = find_source_primary_tables(plan, execution, metric_id)
    if subset_df is None or parent_df is None:
        raise ValueError(
            f"comparison run {run.run_id} requires executed subset and parent_l3 "
            f"primary tables for metric_id={metric_id}"
        )
    share = compute_subset_l3_share(
        subset_primary=subset_df,
        parent_primary=parent_df,
        metric_id=metric_id,  # type: ignore[arg-type]
    )
    return [(run.table_id, share, "primary")]


def find_source_primary_tables(
    plan: AnalysisPlan,
    execution: ExecutionResult,
    metric_id: str,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    primary_table_id = _PRIMARY_TABLE_BY_METRIC.get(metric_id)
    if not primary_table_id:
        return None, None

    subset_section_id = _first_section_id(plan, scope_kind="subset", metric_id=metric_id)
    parent_section_id = _first_section_id(plan, scope_kind="parent_l3", metric_id=metric_id)
    if not subset_section_id or not parent_section_id:
        return None, None

    subset_df = execution.primary_table(
        section_id=subset_section_id,
        metric_id=metric_id,
        table_id=primary_table_id,
    )
    parent_df = execution.primary_table(
        section_id=parent_section_id,
        metric_id=metric_id,
        table_id=primary_table_id,
    )
    return subset_df, parent_df


def _first_section_id(plan: AnalysisPlan, *, scope_kind: str, metric_id: str) -> str | None:
    for item in plan.runs:
        if item.scope_kind == scope_kind and item.metric_id == metric_id and item.status == "executable":
            return item.section_id
    return None
