"""Step 4: verify whether execution results answer the blueprint."""

from __future__ import annotations

from catemate.execution.result_collector import ExecutionResult
from catemate.orchestration.module_capability import metric_key
from catemate.orchestration.schemas import (
    AnalysisPlan,
    MetricRecommendation,
    ReportBlueprint,
    SolveVerdict,
    UnsolvedSection,
)


def verify_solution(
    blueprint: ReportBlueprint,
    plan: AnalysisPlan,
    execution: ExecutionResult,
    *,
    user_declined_data: bool = False,
    adopted_recommendations: list[MetricRecommendation] | None = None,
) -> SolveVerdict:
    solved: list[str] = []
    unsolved: list[UnsolvedSection] = []
    adopted = adopted_recommendations or []
    adopted_by_section: dict[str, list[str]] = {}
    for item in adopted:
        adopted_by_section.setdefault(item.section_id, []).append(item.metric_id)

    tables_by_section_metric: dict[str, list[str]] = {}
    for item in execution.tables:
        section_id = item.get("section_id", "")
        metric_id = item.get("metric_id", "")
        table_id = item.get("table_id", "")
        if section_id and metric_id and table_id:
            tables_by_section_metric.setdefault(metric_key(section_id, metric_id), []).append(table_id)

    for section in blueprint.sections:
        section_runs = [run for run in plan.runs if run.section_id == section.section_id]
        if not section_runs:
            unsolved.append(
                UnsolvedSection(
                    section_id=section.section_id,
                    reason="no_plan_runs",
                    suggestion="为该 section 生成可执行 PlanRun",
                )
            )
            continue

        blocked = [run for run in section_runs if run.status == "blocked_until_rawdata"]
        if blocked:
            unsolved.append(
                UnsolvedSection(
                    section_id=section.section_id,
                    reason="blocked_until_rawdata",
                    suggestion=f"补充源表 {blocked[0].missing} 或在澄清流中选择跳过",
                )
            )
            continue

        primary_run = section_runs[0]
        required_metrics = [primary_run.metric_id]
        for metric_id in adopted_by_section.get(section.section_id, []):
            if metric_id not in required_metrics:
                required_metrics.append(metric_id)

        missing_metrics: list[str] = []
        for metric_id in required_metrics:
            key = metric_key(section.section_id, metric_id)
            tables = tables_by_section_metric.get(key, [])
            non_empty = [
                table_id
                for table_id in tables
                if execution.dataframes.get(table_id) is not None
                and len(execution.dataframes[table_id]) > 0
            ]
            if not non_empty:
                missing_metrics.append(metric_id)

        if not missing_metrics:
            solved.append(section.section_id)
        elif primary_run.metric_id in missing_metrics:
            unsolved.append(
                UnsolvedSection(
                    section_id=section.section_id,
                    reason="no_data_tables",
                    suggestion="修订报告形态或补充数据源后重试",
                )
            )
        else:
            unsolved.append(
                UnsolvedSection(
                    section_id=section.section_id,
                    reason="missing_supplementary_metrics",
                    suggestion=f"补跑辅助指标: {', '.join(missing_metrics)}",
                )
            )

    if user_declined_data and unsolved:
        return SolveVerdict(
            verdict="partial",
            solved_sections=solved,
            unsolved_sections=unsolved,
            loop_iteration=blueprint.loop_iteration,
            exit_reason="user_declined_data",
            notes=["用户选择不再补充数据，以 partial 状态交付"],
        )

    if not unsolved:
        return SolveVerdict(
            verdict="solved",
            solved_sections=solved,
            unsolved_sections=[],
            loop_iteration=blueprint.loop_iteration,
            exit_reason="solved",
        )

    blocked_only = all(u.reason == "blocked_until_rawdata" for u in unsolved)
    if blocked_only:
        return SolveVerdict(
            verdict="retry",
            solved_sections=solved,
            unsolved_sections=unsolved,
            loop_iteration=blueprint.loop_iteration,
            notes=["等待数据澄清子循环补齐源表"],
        )

    supplementary_only = all(u.reason == "missing_supplementary_metrics" for u in unsolved)
    if supplementary_only:
        return SolveVerdict(
            verdict="retry",
            solved_sections=solved,
            unsolved_sections=unsolved,
            loop_iteration=blueprint.loop_iteration,
            notes=["待补跑辅助指标以完整回答 section"],
        )

    return SolveVerdict(
        verdict="retry",
        solved_sections=solved,
        unsolved_sections=unsolved,
        loop_iteration=blueprint.loop_iteration,
        notes=["部分子问题未覆盖，将修订 Blueprint 后重试"],
    )
