"""Adapt RequirementPlanningSpec into CategoryAnalysisRequirementSpec."""

from __future__ import annotations

from typing import Any

from catemate.planning.schemas import RequirementPlanningSpec
from catemate.schemas.category_requirement import (
    AnalysisPlanRow,
    CategoryAnalysisRequirementSpec,
    CategoryCandidateRow,
    ChartDataRequirementRow,
    DataRequirementRow,
    RequirementSummaryRow,
)
from catemate.schemas.confirmation import ConfirmationItem
from catemate.schemas.enums import ChartType, ConfirmationStatus


FIT_STATUS = {
    "high": "支持",
    "medium": "部分支持",
    "low": "弱支持",
}


def build_requirement_spec_from_planning(
    case_config: dict[str, Any],
    planning_spec: RequirementPlanningSpec,
    base_spec: CategoryAnalysisRequirementSpec | None = None,
) -> CategoryAnalysisRequirementSpec:
    """Merge planning output into a requirement workbook spec.

    When ``base_spec`` is provided (usual path), keep deterministic source checks /
    preprocess / static confirmation items, then overlay planning-derived rows.
    """
    base = base_spec or CategoryAnalysisRequirementSpec(
        project_name=planning_spec.project_name or str(case_config.get("project_name") or ""),
    )

    summary = list(base.requirement_summary)
    summary = _upsert_summary(summary, "AI规划理解", planning_spec.interpreted_request)
    if planning_spec.assumptions:
        summary = _upsert_summary(summary, "规划假设", "；".join(planning_spec.assumptions))
    if planning_spec.source_notes:
        summary = _upsert_summary(summary, "规划来源说明", "；".join(planning_spec.source_notes))

    category_candidates = _merge_category_candidates(base.category_candidates, planning_spec)
    analysis_plan = _build_analysis_plan(planning_spec) or list(base.analysis_plan)
    data_requirements = _build_data_requirements(planning_spec, case_config) or list(base.data_requirements)
    chart_requirements = _build_chart_requirements(planning_spec) or list(base.chart_requirements)
    confirmation_items = _merge_confirmation_items(base.confirmation_items, planning_spec)

    return CategoryAnalysisRequirementSpec(
        project_name=planning_spec.project_name or base.project_name,
        requirement_summary=summary,
        category_candidates=category_candidates,
        analysis_plan=analysis_plan,
        data_requirements=data_requirements,
        source_checks=list(base.source_checks),
        preprocess_plan=list(base.preprocess_plan),
        chart_requirements=chart_requirements,
        confirmation_items=confirmation_items,
        allowed_final_statuses=list(base.allowed_final_statuses),
        blocking_statuses=list(base.blocking_statuses),
    )


def _upsert_summary(
    rows: list[RequirementSummaryRow],
    field: str,
    content: str,
) -> list[RequirementSummaryRow]:
    if not content:
        return rows
    updated = [row for row in rows if row.field != field]
    updated.append(RequirementSummaryRow(field=field, content=content))
    return updated


def _merge_category_candidates(
    base_candidates: list[CategoryCandidateRow],
    planning_spec: RequirementPlanningSpec,
) -> list[CategoryCandidateRow]:
    planning_rows: list[CategoryCandidateRow] = []
    for item in planning_spec.target_categories:
        parts = [part.strip() for part in item.path.replace("/", ">").split(">") if part.strip()]
        planning_rows.append(
            CategoryCandidateRow(
                user_text=item.path,
                candidate_path=item.path,
                l1=parts[0] if len(parts) > 0 else "",
                l2=parts[1] if len(parts) > 1 else "",
                l3=parts[2] if len(parts) > 2 else "",
                match_type=f"AI规划/{item.level}",
                confirmation_status=ConfirmationStatus.PENDING_CONFIRMATION.value,
                note=(
                    f"confidence={item.confidence:.2f}; {item.reason}".strip("; ")
                    if item.reason or item.confidence
                    else "来自 AI planning spec，待用户确认。"
                ),
            )
        )

    if not planning_rows:
        return list(base_candidates)

    # Prefer planning categories as primary candidates; keep unmatched base rows.
    planning_paths = {row.candidate_path for row in planning_rows}
    retained = [
        row
        for row in base_candidates
        if row.candidate_path and row.candidate_path not in planning_paths
    ]
    return planning_rows + retained


def _build_analysis_plan(planning_spec: RequirementPlanningSpec) -> list[AnalysisPlanRow]:
    rows: list[AnalysisPlanRow] = []
    for module in planning_spec.matched_data_modules:
        limitations = "；".join(module.limitations) if module.limitations else ""
        deps = "、".join(module.required_tables) if module.required_tables else module.module_id
        note_parts = [module.reason]
        if limitations:
            note_parts.append(f"限制：{limitations}")
        rows.append(
            AnalysisPlanRow(
                analysis_block=module.module_name or module.module_id,
                question=module.reason or f"使用数据模块 {module.module_id} 回答该需求",
                support_status=FIT_STATUS.get(module.fit_level, module.fit_level),
                dependencies=deps,
                note="；".join(part for part in note_parts if part),
                module_id=module.module_id,
                planning_reason=module.reason,
            )
        )
    return rows


def _build_data_requirements(
    planning_spec: RequirementPlanningSpec,
    case_config: dict[str, Any],
) -> list[DataRequirementRow]:
    source_notes_text = "；".join(planning_spec.source_notes)
    rows: list[DataRequirementRow] = []
    for module in planning_spec.matched_data_modules:
        tables = module.required_tables or [""]
        for table_id in tables:
            rows.append(
                DataRequirementRow(
                    data_source=module.module_name or module.module_id,
                    field_or_sheet=table_id or module.module_id,
                    is_required="是" if module.fit_level == "high" else "建议",
                    purpose=module.reason or f"支撑模块 {module.module_id}",
                    missing_impact="；".join(module.limitations) if module.limitations else "缺少该表会影响对应分析输出",
                    current_note=f"来自 planning / case={case_config.get('case_id', planning_spec.case_id)}",
                    module_id=module.module_id,
                    table_id=table_id,
                    planning_reason=module.reason,
                    source_notes=source_notes_text,
                )
            )
    return rows


def _build_chart_requirements(planning_spec: RequirementPlanningSpec) -> list[ChartDataRequirementRow]:
    rows: list[ChartDataRequirementRow] = []
    for chart in planning_spec.proposed_charts:
        fields = ", ".join([*chart.metrics, *chart.dimensions]) if (chart.metrics or chart.dimensions) else ""
        chart_type_enum = _safe_chart_type(chart.chart_type)
        y_axis_text = ", ".join(chart.y_axis) if chart.y_axis else ", ".join(chart.metrics)
        rows.append(
            ChartDataRequirementRow(
                chart_page=chart.title or chart.chart_id,
                required_table="; ".join(chart.table_ids) if chart.table_ids else chart.data_module_id,
                fields=fields,
                status="可规划",
                note=chart.reason,
                chart_type=chart_type_enum,
                data_module_id=chart.data_module_id,
                table_ids="; ".join(chart.table_ids),
                grain=chart.grain,
                metrics=", ".join(chart.metrics),
                dimensions=", ".join(chart.dimensions),
                planning_reason=chart.reason,
                chart_intent=chart.chart_intent,
                x_axis=chart.x_axis or "",
                y_axis=y_axis_text,
                series=chart.series or "",
                sort_rule=chart.sort_rule,
                optional_flag="是" if chart.optional else "",
                selection_reason=chart.selection_reason,
            )
        )
    return rows


def _merge_confirmation_items(
    base_items: list[ConfirmationItem],
    planning_spec: RequirementPlanningSpec,
) -> list[ConfirmationItem]:
    planning_items: list[ConfirmationItem] = []
    for question in planning_spec.missing_data_questions:
        label = question.question_id.strip() or "规划确认"
        full_question = question.question.strip()
        planning_items.append(
            ConfirmationItem(
                name=label,
                status=ConfirmationStatus.PENDING_CONFIRMATION,
                suggested_value="",
                reason=full_question or question.reason,
                source="AI规划",
                planning_question_id=question.question_id,
                blocks_ppt_ready=question.blocks_ppt_ready,
            )
        )

    # Keep static base confirmation items first, then planning questions.
    # Deduplicate by name to avoid identical repeats.
    seen_names = {item.name for item in planning_items}
    retained = [item for item in base_items if item.name not in seen_names]
    return retained + planning_items


def _safe_chart_type(value: str) -> ChartType | None:
    try:
        return ChartType(value)
    except ValueError:
        return None
