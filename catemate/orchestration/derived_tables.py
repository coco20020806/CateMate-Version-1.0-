"""Registry for derived/computed output tables (not rawdata sources)."""

from __future__ import annotations

from catemate.orchestration.schemas import ScopeKind

COMPARISON_TABLE_PREFIX = "subset_l3_"
COMPARISON_TABLE_SUFFIX = "_share_by_site_month"


def comparison_table_id(metric_id: str) -> str:
    metric = str(metric_id or "gmv").strip() or "gmv"
    return f"{COMPARISON_TABLE_PREFIX}{metric}{COMPARISON_TABLE_SUFFIX}"


def is_comparison_table_id(table_id: str) -> bool:
    text = str(table_id or "").strip()
    return text.startswith(COMPARISON_TABLE_PREFIX) and text.endswith(COMPARISON_TABLE_SUFFIX)


def is_computed_scope(scope_kind: ScopeKind | str) -> bool:
    return str(scope_kind or "").strip() == "comparison"
