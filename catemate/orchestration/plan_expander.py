"""Expand AnalysisPlan with supplementary metric runs under the same section."""

from __future__ import annotations

from catemate.orchestration.module_capability import metric_key
from catemate.orchestration.schemas import (
    AnalysisPlan,
    MetricRecommendation,
    PlanRun,
    ReportBlueprint,
)


def expand_plan_with_metrics(
    plan: AnalysisPlan,
    blueprint: ReportBlueprint,
    recommendations: list[MetricRecommendation],
) -> tuple[AnalysisPlan, ReportBlueprint]:
    if not recommendations:
        return plan, blueprint

    existing_keys = {
        metric_key(run.section_id, run.metric_id)
        for run in plan.runs
    }
    next_index = len(plan.runs) + 1
    new_runs: list[PlanRun] = list(plan.runs)

    for recommendation in recommendations:
        key = metric_key(recommendation.section_id, recommendation.metric_id)
        if key in existing_keys:
            continue
        base_run = _find_base_run(plan, recommendation.section_id)
        if base_run is None:
            continue
        new_runs.append(
            base_run.model_copy(
                update={
                    "run_id": f"r{next_index}",
                    "metric_id": recommendation.metric_id,
                }
            )
        )
        existing_keys.add(key)
        next_index += 1

    updated_plan = plan.model_copy(update={"runs": new_runs})
    updated_blueprint = _patch_blueprint_metrics(blueprint, new_runs)
    return updated_plan, updated_blueprint


def _find_base_run(plan: AnalysisPlan, section_id: str) -> PlanRun | None:
    for run in plan.runs:
        if run.section_id == section_id and run.status == "executable":
            return run
    return None


def _patch_blueprint_metrics(
    blueprint: ReportBlueprint,
    runs: list[PlanRun],
) -> ReportBlueprint:
    metrics_by_section: dict[str, list[str]] = {}
    for run in runs:
        metrics_by_section.setdefault(run.section_id, [])
        if run.metric_id not in metrics_by_section[run.section_id]:
            metrics_by_section[run.section_id].append(run.metric_id)

    updated_sections = []
    for section in blueprint.sections:
        metrics = metrics_by_section.get(section.section_id)
        if not metrics:
            updated_sections.append(section)
            continue
        merged = list(section.expected_shape.metrics)
        for metric in metrics:
            if metric not in merged:
                merged.append(metric)
        updated_sections.append(
            section.model_copy(
                update={
                    "expected_shape": section.expected_shape.model_copy(
                        update={"metrics": merged}
                    )
                }
            )
        )
    return blueprint.model_copy(update={"sections": updated_sections})
