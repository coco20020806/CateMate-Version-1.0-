"""V2 outer solve loop controller."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from catemate.ai.client import CateMateAIClient
from catemate.execution.result_collector import ExecutionResult
from catemate.execution.runner import execute_analysis_plan_incremental
from catemate.orchestration.blueprint_generator import build_report_blueprint
from catemate.orchestration.catalog_checker import check_plan_catalog_readiness
from catemate.orchestration.metric_advisor import recommend_supplementary_metrics
from catemate.orchestration.module_capability import (
    available_metrics_for_module,
    metric_key,
)
from catemate.orchestration.plan_composer import compose_analysis_plan
from catemate.orchestration.plan_expander import expand_plan_with_metrics
from catemate.orchestration.schemas import MetricRecommendation, SolveLoopState, SolveVerdict
from catemate.orchestration.solve_verifier import verify_solution
from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.scope.executor import execute_scope
from catemate.scope.schemas import ScopeSpec
from catemate.understanding.schemas import RequirementUnderstandingSpec

MAX_METRIC_EXPANSIONS = 3


def run_solve_loop(
    understanding: RequirementUnderstandingSpec,
    *,
    max_iterations: int = 3,
    user_declined_data: bool = False,
    processed_data_dir: Path | None = None,
    ai_client: CateMateAIClient | None = None,
) -> SolveLoopState:
    state = SolveLoopState(max_iterations=max_iterations, user_declined_data=user_declined_data)
    adopted_recommendations: list[MetricRecommendation] = []

    for iteration in range(1, max_iterations + 1):
        state.loop_iteration = iteration
        state.phase = "blueprint"
        blueprint = build_report_blueprint(
            understanding,
            loop_iteration=iteration,
            ai_client=ai_client,
            processed_data_dir=processed_data_dir,
            metadata=state.metadata,
        )
        state.blueprint = blueprint

        state.phase = "compose"
        plan = compose_analysis_plan(blueprint, understanding)
        plan, rawdata_questions = check_plan_catalog_readiness(plan)
        state.plan = plan
        state.rawdata_questions = rawdata_questions

        if rawdata_questions and not user_declined_data:
            state.phase = "data_clarification"
            return state

        state.phase = "catalog_check"
        execution, executed_keys, adopted_recommendations, plan, blueprint = _run_metric_expansion_loop(
            understanding=understanding,
            blueprint=blueprint,
            plan=plan,
            processed_data_dir=processed_data_dir,
            ai_client=ai_client,
            adopted_recommendations=adopted_recommendations,
        )

        state.plan = plan
        state.blueprint = blueprint

        state.phase = "verify"
        verdict = verify_solution(
            blueprint,
            plan,
            execution,
            user_declined_data=user_declined_data,
            adopted_recommendations=adopted_recommendations,
        )
        verdict.loop_iteration = iteration
        state.verdict = verdict
        state.metadata["execution_errors"] = execution.errors
        state.metadata["executed_metric_keys"] = sorted(executed_keys)
        state.metadata["metric_recommendations"] = [
            item.model_dump(mode="json") for item in adopted_recommendations
        ]

        if verdict.verdict in ("solved", "partial"):
            state.phase = "done"
            return state

        if iteration >= max_iterations:
            state.phase = "done"
            state.verdict = verdict.model_copy(
                update={
                    "verdict": "partial",
                    "exit_reason": "max_iterations",
                    "notes": verdict.notes + ["达到最大迭代次数，以 partial 交付"],
                }
            )
            return state

    state.phase = "done"
    return state


def _run_metric_expansion_loop(
    *,
    understanding: RequirementUnderstandingSpec,
    blueprint,
    plan,
    processed_data_dir: Path | None,
    ai_client: CateMateAIClient | None,
    adopted_recommendations: list[MetricRecommendation],
) -> tuple[ExecutionResult, set[str], list[MetricRecommendation], Any, Any]:
    execution = ExecutionResult()
    executed_keys: set[str] = set()
    available_by_run = _available_metrics_by_run(plan, processed_data_dir=processed_data_dir)

    for expansion_round in range(MAX_METRIC_EXPANSIONS + 1):
        batch = execute_analysis_plan_incremental(
            plan,
            executed_keys,
            processed_data_dir=processed_data_dir,
        )
        execution.merge(batch)
        for run in plan.runs:
            if run.status == "executable":
                executed_keys.add(metric_key(run.section_id, run.metric_id))

        recommendations = recommend_supplementary_metrics(
            understanding=understanding,
            blueprint=blueprint,
            plan=plan,
            executed_keys=executed_keys,
            available_by_run=available_by_run,
            ai_client=ai_client,
        )
        if not recommendations:
            break

        adopted_recommendations.extend(recommendations)
        plan, blueprint = expand_plan_with_metrics(plan, blueprint, recommendations)
        available_by_run = _available_metrics_by_run(plan, processed_data_dir=processed_data_dir)

    return execution, executed_keys, adopted_recommendations, plan, blueprint


def _available_metrics_by_run(plan, *, processed_data_dir: Path | None) -> dict[str, list[str]]:
    cache: dict[str, list[str]] = {}
    result: dict[str, list[str]] = {}
    for run in plan.runs:
        if run.status != "executable":
            continue
        scope_cache_key = "|".join(
            [
                run.module_id,
                run.table_id,
                ",".join(run.target_sites),
                run.category_l1,
                run.category_l2,
                run.category_l3,
                str(run.related_concept_pack or ""),
            ]
        )
        if scope_cache_key not in cache:
            frame = execute_scope(
                ScopeSpec(
                    grain=run.grain,
                    table_id=run.table_id,
                    target_sites=run.target_sites,
                    category_l1=run.category_l1,
                    category_l2=run.category_l2,
                    category_l3=run.category_l3,
                    scope_label=run.scope_label,
                    related_concept_pack=(
                        RelatedConceptPack.model_validate(run.related_concept_pack)
                        if run.related_concept_pack
                        else None
                    ),
                    related_min_score=run.related_min_score,
                ),
                processed_data_dir=processed_data_dir,
            )
            cache[scope_cache_key] = available_metrics_for_module(
                run.module_id,
                list(frame.data.columns),
            )
        result[run.run_id] = list(cache[scope_cache_key])
    return result


def save_solve_loop_state(state: SolveLoopState, path: Path) -> Path:
    payload = state.model_dump(mode="json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_solve_loop_state(path: Path) -> SolveLoopState:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return SolveLoopState.model_validate(payload)
