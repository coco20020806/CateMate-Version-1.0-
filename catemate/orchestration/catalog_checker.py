"""Check rawdata catalog readiness for AnalysisPlan runs."""

from __future__ import annotations

from catemate.data.rawdata_catalog import catalog_key, get_catalog_entry, is_catalog_available
from catemate.orchestration.module_source_bindings import (
    grain_requires_scope,
    validate_run_source,
)
from catemate.orchestration.schemas import AnalysisPlan, PlanRun, RawdataClarificationQuestion


def check_plan_catalog_readiness(plan: AnalysisPlan) -> tuple[AnalysisPlan, list[RawdataClarificationQuestion]]:
    """Mark blocked runs and build rawdata clarification questions for missing sources."""
    updated_runs: list[PlanRun] = []
    questions: list[RawdataClarificationQuestion] = []
    seen: set[str] = set()

    for run in plan.runs:
        grain = run.grain
        table_id = run.table_id or _table_id_from_catalog_key(run.required_catalog)
        if not table_id:
            updated_runs.append(run)
            continue

        if not validate_run_source(run.module_id, grain, table_id):
            key = catalog_key(grain, table_id)
            updated_runs.append(
                run.model_copy(
                    update={
                        "status": "blocked_until_rawdata",
                        "table_id": table_id,
                        "missing": key,
                    }
                )
            )
            if key not in seen:
                seen.add(key)
                questions.append(
                    RawdataClarificationQuestion(
                        question_id=f"rawdata_{grain}_{table_id}",
                        question=(
                            f"模块「{run.module_id}」不支持 {grain} 维度源表「{table_id}」，"
                            "请调整分析计划或补充模块源数据绑定。"
                        ),
                        grain=grain,
                        table_id=table_id,
                        catalog_key=key,
                        reason="模块 source_bindings 未允许该 grain/table 组合",
                    )
                )
            continue

        missing_scope = _missing_scope_fields(run)
        if missing_scope:
            key = catalog_key(grain, table_id)
            updated_runs.append(
                run.model_copy(
                    update={
                        "status": "blocked_until_rawdata",
                        "table_id": table_id,
                        "missing": key,
                    }
                )
            )
            if key not in seen:
                seen.add(key)
                questions.append(
                    RawdataClarificationQuestion(
                        question_id=f"rawdata_{grain}_{table_id}",
                        question=(
                            f"缺少 {grain} 维度源表「{table_id}」所需的类目路径"
                            f"（{', '.join(missing_scope)}），请先完成类目映射（L1/L2/L3）。"
                        ),
                        grain=grain,
                        table_id=table_id,
                        catalog_key=key,
                        reason="item 维度源数据按 L3 类目文件夹组织",
                    )
                )
            continue

        category_path = (run.category_l1, run.category_l2, run.category_l3)
        if is_catalog_available(
            grain,
            table_id,
            category_path=category_path if grain == "item" else None,
        ):
            updated_runs.append(
                run.model_copy(update={"status": "executable", "table_id": table_id, "missing": ""})
            )
            continue

        key = catalog_key(grain, table_id)
        entry = get_catalog_entry(table_id) or {}
        updated_runs.append(
            run.model_copy(
                update={
                    "status": "blocked_until_rawdata",
                    "table_id": table_id,
                    "missing": key,
                }
            )
        )
        if key not in seen:
            seen.add(key)
            questions.append(
                RawdataClarificationQuestion(
                    question_id=f"rawdata_{grain}_{table_id}",
                    question=f"缺少 {grain} 维度源表「{table_id}」，请粘贴本地 Excel 文件的完整路径；若暂时无法提供可选择跳过。",
                    grain=grain,
                    table_id=table_id,
                    catalog_key=key,
                    reason=entry.get("description", "分析计划需要此源表"),
                )
            )

    return plan.model_copy(update={"runs": updated_runs}), questions


def all_runs_executable(plan: AnalysisPlan) -> bool:
    return all(run.status == "executable" for run in plan.runs)


def _table_id_from_catalog_key(required_catalog: str) -> str:
    if "/" in required_catalog:
        return required_catalog.split("/", 1)[1]
    return required_catalog


def _missing_scope_fields(run: PlanRun) -> list[str]:
    required = grain_requires_scope(run.module_id, run.grain)
    if not required:
        return []
    values = {
        "category_l1": run.category_l1,
        "category_l2": run.category_l2,
        "category_l3": run.category_l3,
    }
    return [field for field in required if not str(values.get(field, "")).strip()]
