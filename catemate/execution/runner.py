"""Step 3: execute AnalysisPlan runs via Scope + data modules."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from catemate.execution.result_collector import ExecutionResult
from catemate.execution.comparison_runner import run_comparison_tables
from catemate.orchestration.module_registry import is_active_v2_module
from catemate.orchestration.schemas import AnalysisPlan
from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.scope.executor import execute_scope
from catemate.scope.schemas import ScopeSpec

if TYPE_CHECKING:
    from catemate.scope.scope_cache import ScopeCache


def execute_analysis_plan(
    plan: AnalysisPlan,
    *,
    processed_data_dir: Path | None = None,
    skip_keys: set[str] | None = None,
    scope_cache: ScopeCache | None = None,
) -> ExecutionResult:
    result = ExecutionResult()
    skip_keys = skip_keys or set()

    phase1 = [
        run
        for run in plan.runs
        if run.status == "executable" and run.scope_kind != "comparison"
    ]
    phase2 = [
        run
        for run in plan.runs
        if run.status == "executable" and run.scope_kind == "comparison"
    ]

    for run in phase1 + phase2:
        key = f"{run.section_id}:{run.metric_id}"
        if key in skip_keys:
            continue
        try:
            if run.scope_kind == "comparison":
                module_tables = run_comparison_tables(run, plan, result)
            else:
                module_tables = _run_module(
                    run,
                    processed_data_dir=processed_data_dir,
                    scope_cache=scope_cache,
                )
            for table_id, df, kind in module_tables:
                result.add_table(
                    table_id=table_id,
                    dataframe=df,
                    run_id=run.run_id,
                    section_id=run.section_id,
                    module_id=run.module_id,
                    metric_id=run.metric_id,
                    table_kind=kind,
                )
        except Exception as exc:
            result.errors.append(f"{run.run_id}: {exc}")

    return result


def execute_analysis_plan_incremental(
    plan: AnalysisPlan,
    executed_keys: set[str],
    *,
    processed_data_dir: Path | None = None,
    scope_cache: ScopeCache | None = None,
) -> ExecutionResult:
    """Execute only runs whose section_id:metric_id is not yet in executed_keys."""
    return execute_analysis_plan(
        plan,
        processed_data_dir=processed_data_dir,
        skip_keys=set(executed_keys),
        scope_cache=scope_cache,
    )


def _run_module(
    run,
    *,
    processed_data_dir: Path | None = None,
    scope_cache: ScopeCache | None = None,
) -> list[tuple[str, object, str]]:
    import pandas as pd

    if not is_active_v2_module(run.module_id):
        raise ValueError(
            f"module_id={run.module_id} is not active in V2 solve loop; "
            "only status=active contracts in data_modules/ may be executed."
        )

    spec = ScopeSpec(
        grain=run.grain,
        table_id=run.table_id,
        target_sites=run.target_sites,
        category_l1=run.category_l1,
        category_l2=run.category_l2,
        category_l3=run.category_l3,
        scope_label=run.scope_label,
        related_concept_pack=_related_pack_from_run(run),
        related_min_score=run.related_min_score,
    )
    frame = execute_scope(
        spec,
        processed_data_dir=processed_data_dir,
        scope_cache=scope_cache,
        require_rawdata=_requires_rawdata_source(run),
    )

    if run.module_id == "monthly_market_trend":
        from data_modules.monthly_market_trend import ComputeParams, compute, transform

        params = ComputeParams(metric_id=run.metric_id)  # type: ignore[arg-type]
        primary = compute(params, frame)
        derived = transform(primary)
        tables: list[tuple[str, pd.DataFrame, str]] = []
        for table_id, df in primary.items():
            tables.append((table_id, df, "primary"))
        for table_id, df in derived.items():
            tables.append((table_id, df, "derived"))
        return tables

    if run.module_id == "top_sku_info":
        from data_modules.top_sku_info import ComputeParams, compute

        params = ComputeParams(top_n=20, sort_by="both")
        primary = compute(params, frame)
        return [(tid, df, "primary") for tid, df in primary.items()]

    raise ValueError(f"Unsupported module_id={run.module_id}")


def _related_pack_from_run(run) -> RelatedConceptPack | None:
    payload = run.related_concept_pack
    if not payload:
        return None
    return RelatedConceptPack.model_validate(payload)


def _requires_rawdata_source(run) -> bool:
    if getattr(run, "source_kind", "rawdata") == "computed":
        return False
    if run.module_id == "monthly_market_trend" and run.grain in {"category", "item"}:
        return True
    return run.grain in {"category", "item"}
