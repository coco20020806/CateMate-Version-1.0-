"""AI-based module selection from RequirementUnderstandingSpec."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from catemate.ai.client import CateMateAIClient
from catemate.module_selection.context import (
    build_module_registry,
    load_active_data_modules,
    summarize_modules_for_selection,
)
from catemate.module_selection.prompt_builder import build_module_selection_messages
from catemate.module_selection.schemas import (
    ChartRuleSource,
    ModuleDecision,
    ModuleSelectionItem,
    ModuleSelectionPlan,
    SelectedChartIntent,
    SelectionConfidence,
)
from catemate.module_selection.validator import validate_and_normalize_module_selection_plan
from catemate.understanding.schemas import RequirementUnderstandingSpec, UnderstandingStatus


class ModuleSelectionSelector:
    """Select data modules from a requirement understanding spec."""

    def __init__(self, ai_client: CateMateAIClient):
        self.ai_client = ai_client

    def select(
        self,
        understanding_spec: RequirementUnderstandingSpec,
        *,
        data_modules_dir: Path,
        understanding_spec_path: Path | None = None,
    ) -> ModuleSelectionPlan:
        modules = load_active_data_modules(data_modules_dir)
        registry = build_module_registry(modules)

        if understanding_spec.status != UnderstandingStatus.READY_FOR_MODULE_SELECTION:
            return _blocked_plan(
                understanding_spec,
                registry,
                understanding_spec_path=understanding_spec_path,
            )

        summaries = summarize_modules_for_selection(modules)
        messages = build_module_selection_messages(understanding_spec, summaries)
        payload = self.ai_client.complete_json(messages)
        plan = _validate_plan_payload(
            payload,
            understanding_spec=understanding_spec,
            understanding_spec_path=understanding_spec_path,
        )
        return validate_and_normalize_module_selection_plan(plan, registry)


def _blocked_plan(
    understanding_spec: RequirementUnderstandingSpec,
    registry: dict[str, dict[str, Any]],
    *,
    understanding_spec_path: Path | None,
) -> ModuleSelectionPlan:
    reason = (
        f"Understanding status is {understanding_spec.status.value}; "
        "module selection blocked until requirement understanding is ready."
    )
    rejected: list[ModuleSelectionItem] = []
    for module_id, module in sorted(registry.items()):
        rejected.append(
            ModuleSelectionItem(
                module_id=module_id,
                module_name=str(module.get("module_name") or ""),
                decision=ModuleDecision.REJECTED,
                confidence=SelectionConfidence.LOW,
                reason=reason,
                source_tables=_table_ids(module),
                inherited_chart_rules=dict(module.get("chart_rules") or {}),
                inherited_limitations=list(module.get("limitations") or []),
            )
        )

    return ModuleSelectionPlan(
        case_id=understanding_spec.case_id,
        understanding_spec_path=str(understanding_spec_path or ""),
        status="blocked_by_understanding",
        original_request=understanding_spec.original_request,
        understanding_summary=understanding_spec.conversation_summary,
        rejected_modules=rejected,
        global_warnings=[reason],
    )


def _validate_plan_payload(
    payload: dict[str, Any],
    *,
    understanding_spec: RequirementUnderstandingSpec,
    understanding_spec_path: Path | None,
) -> ModuleSelectionPlan:
    normalized = _normalize_plan_payload(payload, understanding_spec=understanding_spec)
    normalized["understanding_spec_path"] = str(understanding_spec_path or "")
    try:
        return ModuleSelectionPlan.model_validate(normalized)
    except ValidationError as exc:
        snippet = str(normalized)[:800]
        raise ValueError(
            "AI returned JSON that failed ModuleSelectionPlan validation. "
            f"Validation error: {exc}. Payload snippet: {snippet!r}"
        ) from exc


def _normalize_plan_payload(
    payload: dict[str, Any],
    *,
    understanding_spec: RequirementUnderstandingSpec,
) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("spec_version", "module_selection_v1")
    normalized.setdefault("case_id", understanding_spec.case_id)
    normalized.setdefault("status", "ready")
    normalized.setdefault("original_request", understanding_spec.original_request)
    normalized.setdefault(
        "understanding_summary",
        normalized.get("understanding_summary") or understanding_spec.conversation_summary,
    )
    normalized.setdefault("global_assumptions", _as_str_list(normalized.get("global_assumptions")))
    normalized.setdefault("global_warnings", _as_str_list(normalized.get("global_warnings")))

    if normalized.get("module_decisions"):
        buckets = _bucket_module_decisions(normalized["module_decisions"])
        normalized.update(buckets)
    else:
        normalized.setdefault("selected_modules", [])
        normalized.setdefault("optional_modules", [])
        normalized.setdefault("rejected_modules", [])
        normalized.setdefault("needs_confirmation_modules", [])

    normalized.pop("module_decisions", None)
    return normalized


def _bucket_module_decisions(decisions: Any) -> dict[str, list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    optional: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    needs_confirmation: list[dict[str, Any]] = []

    for raw in _as_list(decisions):
        if not isinstance(raw, dict):
            continue
        item = _normalize_decision_item(raw)
        decision = item.get("decision")
        if decision == ModuleDecision.SELECTED.value:
            selected.append(item)
        elif decision == ModuleDecision.OPTIONAL.value:
            optional.append(item)
        elif decision == ModuleDecision.NEEDS_CONFIRMATION.value:
            needs_confirmation.append(item)
        else:
            item["decision"] = ModuleDecision.REJECTED.value
            rejected.append(item)

    return {
        "selected_modules": selected,
        "optional_modules": optional,
        "rejected_modules": rejected,
        "needs_confirmation_modules": needs_confirmation,
    }


def _normalize_decision_item(raw: dict[str, Any]) -> dict[str, Any]:
    decision = str(raw.get("decision") or ModuleDecision.REJECTED.value).lower()
    if decision not in {d.value for d in ModuleDecision}:
        decision = ModuleDecision.REJECTED.value

    confidence = str(raw.get("confidence") or SelectionConfidence.MEDIUM.value).lower()
    if confidence not in {c.value for c in SelectionConfidence}:
        confidence = SelectionConfidence.MEDIUM.value

    charts = [
        _normalize_chart_intent(item)
        for item in _as_list(raw.get("selected_chart_intents"))
        if isinstance(item, dict)
    ]

    return {
        "module_id": str(raw.get("module_id") or ""),
        "module_name": str(raw.get("module_name") or ""),
        "decision": decision,
        "confidence": confidence,
        "matched_intents": _as_str_list(raw.get("matched_intents")),
        "matched_user_need": str(raw.get("matched_user_need") or ""),
        "reason": str(raw.get("reason") or "no reason provided"),
        "source_tables": _as_str_list(raw.get("source_tables")),
        "selected_chart_intents": charts,
        "inherited_chart_rules": raw.get("inherited_chart_rules") or {},
        "inherited_limitations": _as_str_list(raw.get("inherited_limitations")),
        "assumptions": _as_str_list(raw.get("assumptions")),
        "confirmation_questions": _as_str_list(raw.get("confirmation_questions")),
    }


def _normalize_chart_intent(raw: dict[str, Any]) -> dict[str, Any]:
    rule_source = str(raw.get("rule_source") or ChartRuleSource.MODULE_DEFAULT.value).lower()
    if rule_source not in {s.value for s in ChartRuleSource}:
        rule_source = ChartRuleSource.MODULE_DEFAULT.value
    top_n = raw.get("top_n")
    if top_n is not None:
        try:
            top_n = int(top_n)
        except (TypeError, ValueError):
            top_n = None
    return {
        "chart_intent": str(raw.get("chart_intent") or ""),
        "chart_title": str(raw.get("chart_title") or ""),
        "chart_type": str(raw.get("chart_type") or "unknown"),
        "source_default_chart": str(raw.get("source_default_chart") or raw.get("chart_intent") or ""),
        "x_axis": raw.get("x_axis"),
        "y_axis": _as_str_list(raw.get("y_axis")),
        "series": raw.get("series"),
        "dimensions": _as_str_list(raw.get("dimensions")),
        "sort_rule": str(raw.get("sort_rule") or ""),
        "top_n": top_n,
        "rule_source": rule_source,
        "override_reason": str(raw.get("override_reason") or ""),
    }


def _table_ids(module: dict[str, Any]) -> list[str]:
    lineage = module.get("lineage") or {}
    ids: list[str] = []
    for item in lineage.get("source_tables") or []:
        if isinstance(item, dict) and item.get("table_id"):
            ids.append(str(item["table_id"]))
    return ids


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value is None or value == "":
        return []
    return [str(value)]
