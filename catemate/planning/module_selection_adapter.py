"""Deterministic adapter: ModuleSelectionPlan -> RequirementPlanningSpec."""

from __future__ import annotations

import re

from catemate.module_selection.schemas import (
    ModuleDecision,
    ModuleSelectionItem,
    ModuleSelectionPlan,
    SelectedChartIntent,
    SelectionConfidence,
)
from catemate.planning.schemas import (
    ChartTypeName,
    PlanningChartProposal,
    PlanningDataModuleMatch,
    PlanningMissingDataQuestion,
    PlanningTargetCategory,
    RequirementPlanningSpec,
)
from catemate.understanding.schemas import RequirementUnderstandingSpec

VALID_CHART_TYPES: set[str] = {"bubble", "bar", "trend", "share", "table", "unknown"}

CONFIDENCE_TO_FIT: dict[SelectionConfidence, str] = {
    SelectionConfidence.HIGH: "high",
    SelectionConfidence.MEDIUM: "medium",
    SelectionConfidence.LOW: "low",
}


def build_planning_spec_from_module_selection(
    *,
    understanding_spec: RequirementUnderstandingSpec,
    module_selection_plan: ModuleSelectionPlan,
) -> RequirementPlanningSpec:
    """Build a RequirementPlanningSpec draft without AI."""
    warnings: list[str] = list(module_selection_plan.global_warnings)
    understood = understanding_spec.understood

    category_label = (
        understood.inferred_category.strip()
        or understood.target_category_text.strip()
        or "目标类目"
    )

    proposed_charts: list[PlanningChartProposal] = []
    chart_modules = (
        list(module_selection_plan.selected_modules)
        + list(module_selection_plan.needs_confirmation_modules)
        + list(module_selection_plan.optional_modules)
    )

    for module in chart_modules:
        is_optional = module.decision == ModuleDecision.OPTIONAL
        if not module.selected_chart_intents:
            warnings.append(
                f"{module.module_id}: selected module has no chart intents; skipped chart generation."
            )
            continue
        for chart in module.selected_chart_intents:
            proposed_charts.append(
                _chart_proposal_from_selection(
                    module=module,
                    chart=chart,
                    category_label=category_label,
                    is_optional=is_optional,
                )
            )

    matched_modules = [_module_match_from_selection(module) for module in chart_modules]
    source_notes = _build_source_notes(module_selection_plan)
    assumptions = _build_assumptions(understanding_spec, module_selection_plan)
    missing_questions = _build_missing_questions(understanding_spec, module_selection_plan)

    return RequirementPlanningSpec(
        case_id=module_selection_plan.case_id or understanding_spec.case_id,
        project_name=_build_project_name(understanding_spec, module_selection_plan),
        interpreted_request=(
            module_selection_plan.understanding_summary
            or understanding_spec.conversation_summary
            or understanding_spec.original_request
        ),
        target_categories=_build_target_categories(understanding_spec),
        matched_data_modules=matched_modules,
        proposed_charts=proposed_charts,
        missing_data_questions=missing_questions,
        assumptions=assumptions,
        source_notes=source_notes,
        validation_warnings=_unique(warnings),
    )


def validate_planning_spec_against_module_selection(
    planning_spec: RequirementPlanningSpec,
    module_selection_plan: ModuleSelectionPlan,
) -> list[str]:
    """Return validation warnings; empty means no serious inconsistency detected."""
    issues: list[str] = []

    module_map = {
        item.module_id: item
        for item in module_selection_plan.all_items()
        if item.decision != ModuleDecision.REJECTED
    }
    rejected_ids = {item.module_id for item in module_selection_plan.rejected_modules}

    for chart in planning_spec.proposed_charts:
        if chart.data_module_id in rejected_ids:
            issues.append(
                f"SERIOUS: proposed chart {chart.chart_id} uses rejected module {chart.data_module_id}"
            )

        module = module_map.get(chart.data_module_id)
        if module is None:
            issues.append(
                f"SERIOUS: proposed chart {chart.chart_id} references unknown/non-chart module "
                f"{chart.data_module_id}"
            )
            continue

        if chart.optional and module.decision != ModuleDecision.OPTIONAL:
            issues.append(
                f"Chart {chart.chart_id} marked optional but module decision is {module.decision.value}"
            )
        if not chart.optional and module.decision == ModuleDecision.OPTIONAL:
            issues.append(
                f"Chart {chart.chart_id} not marked optional but module decision is optional"
            )

        intent_ids = {item.chart_intent for item in module.selected_chart_intents}
        if chart.chart_intent and chart.chart_intent not in intent_ids:
            issues.append(
                f"SERIOUS: chart_intent {chart.chart_intent!r} not in module "
                f"{module.module_id} selected_chart_intents"
            )

        if chart.table_ids and set(chart.table_ids) != set(module.source_tables):
            if set(chart.table_ids) - set(module.source_tables):
                issues.append(
                    f"Chart {chart.chart_id} table_ids {chart.table_ids} "
                    f"not subset of module source_tables {module.source_tables}"
                )

        source_chart = _find_chart_intent(module, chart.chart_intent)
        if source_chart and chart.chart_type != _normalize_chart_type(source_chart.chart_type):
            issues.append(
                f"Chart {chart.chart_id} chart_type {chart.chart_type} "
                f"!= selection chart_type {source_chart.chart_type}"
            )

    expected_chart_count = sum(
        len(module.selected_chart_intents)
        for module in (
            module_selection_plan.selected_modules
            + module_selection_plan.needs_confirmation_modules
            + module_selection_plan.optional_modules
        )
    )
    if len(planning_spec.proposed_charts) != expected_chart_count:
        issues.append(
            f"Chart count mismatch: planning has {len(planning_spec.proposed_charts)}, "
            f"selection expects {expected_chart_count}"
        )

    return issues


def has_serious_validation_issues(issues: list[str]) -> bool:
    return any(issue.startswith("SERIOUS:") for issue in issues)


def _chart_proposal_from_selection(
    *,
    module: ModuleSelectionItem,
    chart: SelectedChartIntent,
    category_label: str,
    is_optional: bool,
) -> PlanningChartProposal:
    chart_type = _normalize_chart_type(chart.chart_type)
    metrics = list(chart.y_axis or [])
    dimensions = _build_chart_dimensions(chart_type, chart)
    grain = _build_grain(chart_type, chart)

    selection_reason = module.reason
    if module.matched_user_need:
        selection_reason = f"{selection_reason}；匹配需求：{module.matched_user_need}"
    if module.decision == ModuleDecision.NEEDS_CONFIRMATION:
        selection_reason = f"{selection_reason}；模块待用户确认"
    if is_optional:
        selection_reason = f"{selection_reason}；optional module"

    title = _render_title(chart.chart_title, category_label)
    if is_optional and "（可选）" not in title:
        title = f"{title}（可选）"

    planning_reason = "；".join(
        part
        for part in [
            selection_reason,
            f"chart_intent={chart.chart_intent}",
            chart.override_reason,
        ]
        if part
    )

    return PlanningChartProposal(
        chart_id=_safe_chart_id(module.module_id, chart.chart_intent),
        title=title,
        chart_type=chart_type,
        data_module_id=module.module_id,
        table_ids=list(module.source_tables),
        grain=grain,
        metrics=metrics,
        dimensions=dimensions,
        reason=planning_reason,
        chart_intent=chart.chart_intent,
        x_axis=chart.x_axis,
        y_axis=list(chart.y_axis or []),
        series=chart.series,
        sort_rule=chart.sort_rule or "",
        top_n=chart.top_n,
        rule_source=str(chart.rule_source.value if hasattr(chart.rule_source, "value") else chart.rule_source),
        module_decision=module.decision.value,
        selection_reason=selection_reason,
        optional=is_optional,
    )


def _module_match_from_selection(module: ModuleSelectionItem) -> PlanningDataModuleMatch:
    fit = CONFIDENCE_TO_FIT.get(module.confidence, "medium")
    if module.decision == ModuleDecision.OPTIONAL:
        fit = "low"
    elif module.decision == ModuleDecision.NEEDS_CONFIRMATION:
        fit = "medium"

    reason = module.reason
    if module.decision == ModuleDecision.OPTIONAL:
        reason = f"[optional] {reason}"
    elif module.decision == ModuleDecision.NEEDS_CONFIRMATION:
        reason = f"[needs_confirmation] {reason}"

    return PlanningDataModuleMatch(
        module_id=module.module_id,
        module_name=module.module_name,
        fit_level=fit,  # type: ignore[arg-type]
        reason=reason,
        required_tables=list(module.source_tables),
        limitations=list(module.inherited_limitations),
    )


def _build_target_categories(
    understanding_spec: RequirementUnderstandingSpec,
) -> list[PlanningTargetCategory]:
    understood = understanding_spec.understood
    level = understood.category_level_hint if understood.category_level_hint in {"L1", "L2", "L3"} else "unknown"
    rows: list[PlanningTargetCategory] = []

    if understood.inferred_category.strip():
        rows.append(
            PlanningTargetCategory(
                level=level,  # type: ignore[arg-type]
                path=understood.inferred_category.strip(),
                confidence=0.85,
                reason="来自 requirement understanding inferred_category",
            )
        )
    if (
        understood.target_category_text.strip()
        and understood.target_category_text.strip() != understood.inferred_category.strip()
    ):
        rows.append(
            PlanningTargetCategory(
                level="unknown",
                path=understood.target_category_text.strip(),
                confidence=0.75,
                reason="来自 requirement understanding target_category_text",
            )
        )
    return rows


def _build_source_notes(plan: ModuleSelectionPlan) -> list[str]:
    notes: list[str] = []
    notes.append(f"Module selection status: {plan.status}")
    if plan.understanding_summary:
        notes.append(f"Understanding summary: {plan.understanding_summary}")
    for module in plan.rejected_modules:
        notes.append(f"Rejected module {module.module_id}: {module.reason}")
    for module in plan.selected_modules + plan.optional_modules + plan.needs_confirmation_modules:
        if module.inherited_limitations:
            notes.append(
                f"Module {module.module_id} limitations: "
                + "；".join(module.inherited_limitations[:3])
            )
    return _unique(notes)


def _build_assumptions(
    understanding_spec: RequirementUnderstandingSpec,
    plan: ModuleSelectionPlan,
) -> list[str]:
    assumptions = [item.content for item in understanding_spec.assumptions if item.content]
    assumptions.extend(plan.global_assumptions)
    for module in plan.all_items():
        assumptions.extend(module.assumptions)
    if understanding_spec.understood.metric_definitions:
        for key, value in understanding_spec.understood.metric_definitions.items():
            assumptions.append(f"{key}: {value}")
    return _unique(assumptions)


def _build_missing_questions(
    understanding_spec: RequirementUnderstandingSpec,
    plan: ModuleSelectionPlan,
) -> list[PlanningMissingDataQuestion]:
    questions: list[PlanningMissingDataQuestion] = []
    for module in plan.needs_confirmation_modules:
        for idx, question in enumerate(module.confirmation_questions, start=1):
            questions.append(
                PlanningMissingDataQuestion(
                    question_id=f"{module.module_id}_confirm_{idx}",
                    question=question,
                    reason=f"模块 {module.module_id} 需要确认",
                    blocks_ppt_ready=False,
                )
            )
    return questions


def _build_project_name(
    understanding_spec: RequirementUnderstandingSpec,
    plan: ModuleSelectionPlan,
) -> str:
    understood = understanding_spec.understood
    if understood.inferred_category.strip():
        sites = "、".join(understood.target_sites) if understood.target_sites else ""
        if sites:
            return f"{sites} {understood.inferred_category} 类目分析"
        return f"{understood.inferred_category} 类目分析"
    return plan.case_id or understanding_spec.case_id or "类目分析"


def _build_chart_dimensions(chart_type: ChartTypeName, chart: SelectedChartIntent) -> list[str]:
    dimensions: list[str] = []
    for field in chart.dimensions or []:
        if field and field not in dimensions:
            dimensions.append(field)

    if chart_type == "trend":
        if chart.x_axis and chart.x_axis not in dimensions:
            dimensions.insert(0, chart.x_axis)
        if chart.series and chart.series not in dimensions:
            dimensions.append(chart.series)
    elif chart_type == "share":
        if chart.x_axis and chart.x_axis not in dimensions:
            dimensions.append(chart.x_axis)
    elif chart_type == "bar":
        if chart.x_axis and chart.x_axis not in dimensions:
            dimensions.insert(0, chart.x_axis)
    elif chart_type == "table":
        pass
    else:
        if chart.x_axis and chart.x_axis not in dimensions:
            dimensions.append(chart.x_axis)
        if chart.series and chart.series not in dimensions:
            dimensions.append(chart.series)
    return dimensions


def _build_grain(chart_type: ChartTypeName, chart: SelectedChartIntent) -> str:
    parts: list[str] = []
    if chart.x_axis:
        parts.append(chart.x_axis)
    if chart.series:
        parts.append(chart.series)
    if not parts and chart.dimensions:
        parts.extend(chart.dimensions[:2])
    if chart_type == "trend" and chart.x_axis:
        return f"time={chart.x_axis}" + (f" x {chart.series}" if chart.series else "")
    return " x ".join(parts)


def _render_title(template: str, category_label: str) -> str:
    title = (template or "").replace("{category}", category_label).replace("{month}", "最新月")
    return title.strip() or category_label


def _safe_chart_id(module_id: str, chart_intent: str) -> str:
    raw = f"{module_id}_{chart_intent}"
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", raw)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe[:96] or "chart"


def _normalize_chart_type(value: str) -> ChartTypeName:
    normalized = str(value or "unknown").strip().lower()
    if normalized in VALID_CHART_TYPES:
        return normalized  # type: ignore[return-value]
    return "unknown"


def _find_chart_intent(
    module: ModuleSelectionItem,
    chart_intent: str,
) -> SelectedChartIntent | None:
    for chart in module.selected_chart_intents:
        if chart.chart_intent == chart_intent:
            return chart
    return None


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
