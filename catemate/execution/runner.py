"""Step 3: execute AnalysisPlan runs via Scope + data modules."""

from __future__ import annotations

from pathlib import Path

from catemate.execution.result_collector import ExecutionResult
from catemate.orchestration.module_registry import is_active_v2_module
from catemate.orchestration.schemas import AnalysisPlan
from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.scope.executor import execute_scope
from catemate.scope.schemas import ScopeSpec


def execute_analysis_plan(
    plan: AnalysisPlan,
    *,
    processed_data_dir: Path | None = None,
    skip_keys: set[str] | None = None,
) -> ExecutionResult:
    result = ExecutionResult()
    skip_keys = skip_keys or set()

    for run in plan.runs:
        if run.status != "executable":
            continue
        key = f"{run.section_id}:{run.metric_id}"
        if key in skip_keys:
            continue
        try:
            module_tables = _run_module(run, processed_data_dir=processed_data_dir)
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
) -> ExecutionResult:
    """Execute only runs whose section_id:metric_id is not yet in executed_keys."""
    return execute_analysis_plan(
        plan,
        processed_data_dir=processed_data_dir,
        skip_keys=set(executed_keys),
    )


def _run_module(run, *, processed_data_dir: Path | None = None) -> list[tuple[str, object, str]]:
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
    frame = execute_scope(spec, processed_data_dir=processed_data_dir)

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
