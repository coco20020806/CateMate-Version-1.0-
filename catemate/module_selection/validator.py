"""Deterministic validation and normalization for module selection plans."""

from __future__ import annotations

from typing import Any

from catemate.module_selection.schemas import (
    ChartRuleSource,
    ModuleDecision,
    ModuleSelectionItem,
    ModuleSelectionPlan,
    SelectedChartIntent,
    SelectionConfidence,
)

INTENT_CHART_HINTS: dict[str, list[str]] = {
    "market_trend": ["monthly_trend", "market_history_trend", "monthly_performance_trend"],
    "site_comparison": ["site_comparison", "category_site_comparison"],
    "daily_performance": ["monthly_performance_trend", "daily_performance_trend", "cncb_site_penetration"],
    "price_tier": ["price_tier_distribution", "price_tier_share", "current_vs_prior"],
    "top_listing": ["top_listing_table", "listing_price_reference"],
    "top_shop": ["top_shop_table", "channel_contribution"],
    "keywords": ["keyword_table", "keyword_growth_bar"],
    "price_reference": ["top_listing_table", "listing_price_reference", "aov_by_site"],
    "category_mapping": ["monthly_trend", "keyword_table"],
}


def validate_and_normalize_module_selection_plan(
    plan: ModuleSelectionPlan,
    module_registry: dict[str, dict[str, Any]],
) -> ModuleSelectionPlan:
    """Validate coverage and enrich module selection items from registry."""
    updated = plan.model_copy(deep=True)
    warnings = list(updated.global_warnings)

    items_by_id: dict[str, ModuleSelectionItem] = {}
    for item in updated.all_items():
        if item.module_id in items_by_id:
            warnings.append(f"Duplicate module_id in plan: {item.module_id}")
        items_by_id[item.module_id] = item

    unknown_ids = [mid for mid in items_by_id if mid not in module_registry]
    for module_id in unknown_ids:
        warnings.append(f"Unknown module_id removed from plan: {module_id}")
        items_by_id.pop(module_id, None)

    for module_id, module in module_registry.items():
        if module_id in items_by_id:
            items_by_id[module_id] = _normalize_item(items_by_id[module_id], module, warnings)
        else:
            warnings.append(f"AI missed module {module_id}; auto-added as rejected.")
            items_by_id[module_id] = ModuleSelectionItem(
                module_id=module_id,
                module_name=str(module.get("module_name") or ""),
                decision=ModuleDecision.REJECTED,
                confidence=SelectionConfidence.LOW,
                reason="not selected by AI; no matching need detected",
                source_tables=_registry_table_ids(module),
                inherited_chart_rules=dict(module.get("chart_rules") or {}),
                inherited_limitations=list(module.get("limitations") or []),
            )

    selected: list[ModuleSelectionItem] = []
    optional: list[ModuleSelectionItem] = []
    rejected: list[ModuleSelectionItem] = []
    needs_confirmation: list[ModuleSelectionItem] = []

    for module_id in sorted(module_registry):
        item = items_by_id[module_id]
        if item.decision == ModuleDecision.SELECTED:
            selected.append(item)
        elif item.decision == ModuleDecision.OPTIONAL:
            optional.append(item)
        elif item.decision == ModuleDecision.NEEDS_CONFIRMATION:
            needs_confirmation.append(item)
        else:
            rejected.append(item)

    updated.selected_modules = selected
    updated.optional_modules = optional
    updated.rejected_modules = rejected
    updated.needs_confirmation_modules = needs_confirmation
    updated.global_warnings = _unique(warnings)
    return updated


def summarize_module_selection_plan(plan: ModuleSelectionPlan) -> dict[str, Any]:
    """Human-readable summary for CLI output."""
    return {
        "case_id": plan.case_id,
        "status": plan.status,
        "selected_module_ids": [item.module_id for item in plan.selected_modules],
        "optional_module_ids": [item.module_id for item in plan.optional_modules],
        "needs_confirmation_module_ids": [item.module_id for item in plan.needs_confirmation_modules],
        "rejected_count": len(plan.rejected_modules),
        "warnings_count": len(plan.global_warnings),
        "selected_chart_intents": {
            item.module_id: [chart.chart_intent for chart in item.selected_chart_intents]
            for item in plan.selected_modules + plan.optional_modules + plan.needs_confirmation_modules
        },
    }


def _normalize_item(
    item: ModuleSelectionItem,
    module: dict[str, Any],
    warnings: list[str],
) -> ModuleSelectionItem:
    module_id = str(module.get("module_id") or item.module_id)
    item = item.model_copy(
        update={
            "module_id": module_id,
            "module_name": item.module_name or str(module.get("module_name") or ""),
            "inherited_chart_rules": dict(module.get("chart_rules") or {}),
            "inherited_limitations": list(module.get("limitations") or []),
        }
    )

    if not item.source_tables:
        item.source_tables = _registry_table_ids(module)

    if item.decision in {
        ModuleDecision.SELECTED,
        ModuleDecision.OPTIONAL,
        ModuleDecision.NEEDS_CONFIRMATION,
    }:
        item.selected_chart_intents = _normalize_chart_intents(
            item.selected_chart_intents,
            module,
            item.matched_intents,
            warnings,
        )
        if not item.selected_chart_intents:
            warnings.append(
                f"{module_id}: no selected_chart_intents after normalization; "
                "could not auto-match from default_charts."
            )

    return item


def _normalize_chart_intents(
    charts: list[SelectedChartIntent],
    module: dict[str, Any],
    matched_intents: list[str],
    warnings: list[str],
) -> list[SelectedChartIntent]:
    default_charts = _index_default_charts(module)
    allowed_fields = _module_allowed_fields(module)
    normalized: list[SelectedChartIntent] = []

    if not charts:
        charts = _auto_pick_charts(module, matched_intents)

    for chart in charts:
        default = default_charts.get(chart.chart_intent)
        if default is None:
            if chart.rule_source == ChartRuleSource.SYSTEM_INFERRED and chart.override_reason.strip():
                normalized.append(chart)
            else:
                warnings.append(
                    f"{module.get('module_id')}: chart_intent {chart.chart_intent!r} "
                    "not in default_charts; dropped or needs override_reason."
                )
            continue

        normalized.append(
            _merge_chart_with_default(chart, default, allowed_fields, module, warnings)
        )

    if not normalized:
        normalized = [
            _chart_from_default(default_charts[intent_key], allowed_fields, module, warnings)
            for intent_key in _auto_pick_chart_intent_ids(module, matched_intents)
            if intent_key in default_charts
        ]

    return normalized


def _merge_chart_with_default(
    chart: SelectedChartIntent,
    default: dict[str, Any],
    allowed_fields: set[str],
    module: dict[str, Any],
    warnings: list[str],
) -> SelectedChartIntent:
    chart_type = chart.chart_type or str(default.get("default_chart_type") or "unknown")
    merged = chart.model_copy(
        update={
            "chart_title": chart.chart_title or str(default.get("title_template") or ""),
            "chart_type": chart_type,
            "source_default_chart": chart.source_default_chart or chart.chart_intent,
            "x_axis": chart.x_axis if chart.x_axis is not None else default.get("x_axis"),
            "y_axis": chart.y_axis or list(default.get("y_axis") or []),
            "series": chart.series if chart.series is not None else default.get("series"),
            "dimensions": chart.dimensions or list(default.get("dimensions") or []),
            "sort_rule": chart.sort_rule or str(default.get("sort_rule") or ""),
            "top_n": chart.top_n if chart.top_n is not None else default.get("top_n"),
            "rule_source": chart.rule_source or ChartRuleSource.MODULE_DEFAULT,
        }
    )
    _warn_unknown_fields(module.get("module_id", ""), merged, allowed_fields, warnings)
    return merged


def _chart_from_default(
    default: dict[str, Any],
    allowed_fields: set[str],
    module: dict[str, Any],
    warnings: list[str],
) -> SelectedChartIntent:
    chart_intent = str(default.get("chart_intent") or "")
    chart = SelectedChartIntent(
        chart_intent=chart_intent,
        chart_title=str(default.get("title_template") or ""),
        chart_type=str(default.get("default_chart_type") or "unknown"),
        source_default_chart=chart_intent,
        x_axis=default.get("x_axis"),
        y_axis=list(default.get("y_axis") or []),
        series=default.get("series"),
        dimensions=list(default.get("dimensions") or []),
        sort_rule=str(default.get("sort_rule") or ""),
        top_n=default.get("top_n"),
        rule_source=ChartRuleSource.MODULE_DEFAULT,
    )
    _warn_unknown_fields(module.get("module_id", ""), chart, allowed_fields, warnings)
    return chart


def _auto_pick_charts(
    module: dict[str, Any],
    matched_intents: list[str],
) -> list[SelectedChartIntent]:
    default_charts = _index_default_charts(module)
    picked: list[SelectedChartIntent] = []
    for intent_key in _auto_pick_chart_intent_ids(module, matched_intents):
        default = default_charts.get(intent_key)
        if default:
            picked.append(
                SelectedChartIntent(
                    chart_intent=intent_key,
                    chart_title=str(default.get("title_template") or ""),
                    chart_type=str(default.get("default_chart_type") or "unknown"),
                    source_default_chart=intent_key,
                    x_axis=default.get("x_axis"),
                    y_axis=list(default.get("y_axis") or []),
                    series=default.get("series"),
                    dimensions=list(default.get("dimensions") or []),
                    sort_rule=str(default.get("sort_rule") or ""),
                    top_n=default.get("top_n"),
                    rule_source=ChartRuleSource.MODULE_DEFAULT,
                )
            )
    return picked


def _auto_pick_chart_intent_ids(module: dict[str, Any], matched_intents: list[str]) -> list[str]:
    default_charts = module.get("default_charts") or []
    if not isinstance(default_charts, list) or not default_charts:
        return []

    module_id = str(module.get("module_id") or "")
    picks: list[str] = []

    for intent in matched_intents:
        intent_l = str(intent).lower()
        for hint in INTENT_CHART_HINTS.get(intent_l, []):
            for chart in default_charts:
                if not isinstance(chart, dict):
                    continue
                chart_intent = str(chart.get("chart_intent") or "")
                if hint in chart_intent and chart_intent not in picks:
                    picks.append(chart_intent)

    if picks:
        return picks[:3]

    if module_id == "dashboard_top_listing":
        return ["top_listing_table"]
    if module_id == "dashboard_keywords":
        return ["keyword_table"]
    if module_id == "dashboard_price_tier_distribution":
        return ["price_tier_distribution"]
    if module_id == "rm_monthly_category_performance":
        return ["monthly_trend"]
    if module_id == "dashboard_history_market_trend":
        return ["market_history_trend"]

    first = default_charts[0]
    if isinstance(first, dict) and first.get("chart_intent"):
        return [str(first["chart_intent"])]
    return []


def _index_default_charts(module: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for chart in module.get("default_charts") or []:
        if isinstance(chart, dict) and chart.get("chart_intent"):
            indexed[str(chart["chart_intent"])] = chart
    return indexed


def _module_allowed_fields(module: dict[str, Any]) -> set[str]:
    allowed: set[str] = set()
    fields = module.get("fields") or {}
    if isinstance(fields, dict):
        for group in ("dimensions", "metrics"):
            for item in fields.get(group) or []:
                if isinstance(item, dict) and item.get("field"):
                    allowed.add(str(item["field"]))
    for item in module.get("derived_metrics") or []:
        if isinstance(item, dict) and item.get("metric_id"):
            allowed.add(str(item["metric_id"]))
    return allowed


def _warn_unknown_fields(
    module_id: str,
    chart: SelectedChartIntent,
    allowed_fields: set[str],
    warnings: list[str],
) -> None:
    candidates: list[str | None] = []
    candidates.append(chart.x_axis)
    candidates.extend(chart.y_axis)
    candidates.append(chart.series)
    candidates.extend(chart.dimensions)
    for field in candidates:
        if not field:
            continue
        if field not in allowed_fields:
            warnings.append(f"{module_id}: field {field!r} not in module fields/derived_metrics.")


def _registry_table_ids(module: dict[str, Any]) -> list[str]:
    lineage = module.get("lineage") or {}
    table_ids: list[str] = []
    for item in lineage.get("source_tables") or []:
        if isinstance(item, dict) and item.get("table_id"):
            table_ids.append(str(item["table_id"]))
    return table_ids


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
