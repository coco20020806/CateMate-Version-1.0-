"""Generate CategoryAnalysisCaseConfig from natural-language requests."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from catemate.ai.client import CateMateAIClient
from catemate.case_generation.confirmation_enrichment import enrich_confirmation_templates
from catemate.case_generation.prompt_builder import build_case_config_messages
from catemate.schemas.category_requirement import CategoryAnalysisCaseConfig

__all__ = ["CaseConfigGenerator", "enrich_confirmation_templates"]

VALID_CHART_TYPES = {"bubble", "bar", "trend", "share", "table"}


class CaseConfigGenerator:
    """AI-based draft generator for CategoryAnalysisCaseConfig."""

    def __init__(self, ai_client: CateMateAIClient):
        self.ai_client = ai_client

    def generate(
        self,
        request_text: str,
        reference_case_configs: list[dict[str, Any]] | None = None,
        data_module_summaries: list[dict[str, Any]] | None = None,
    ) -> CategoryAnalysisCaseConfig:
        messages = build_case_config_messages(
            request_text=request_text,
            reference_case_configs=reference_case_configs,
            data_module_summaries=data_module_summaries,
        )
        payload = _normalize_case_payload(self.ai_client.complete_json(messages))
        try:
            config = CategoryAnalysisCaseConfig.model_validate(payload)
            return enrich_confirmation_templates(config)
        except ValidationError as exc:
            snippet = str(payload)[:800]
            raise ValueError(
                "AI returned JSON that failed CategoryAnalysisCaseConfig validation. "
                f"Validation error: {exc}. Payload snippet: {snippet!r}"
            ) from exc


def _normalize_case_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize common near-miss keys from LLM output into schema keys."""
    normalized = dict(payload)

    normalized.setdefault("delivery_format", "Excel")
    normalized.setdefault("delivery_audience", "待确认")
    normalized.setdefault("time_range", "使用源数据可覆盖范围，待确认")
    normalized.setdefault("target_sites", [])
    normalized.setdefault("category_keywords", [])

    normalized["data_requirements"] = [
        _normalize_data_requirement(item)
        for item in _as_list(normalized.get("data_requirements"))
        if isinstance(item, dict)
    ]
    normalized["preprocess_plan"] = [
        _normalize_preprocess_step(item)
        for item in _as_list(normalized.get("preprocess_plan"))
        if isinstance(item, dict)
    ]
    normalized["analysis_plan"] = [
        _normalize_analysis_plan(item)
        for item in _as_list(normalized.get("analysis_plan"))
        if isinstance(item, dict)
    ]
    normalized["chart_requirements"] = [
        _normalize_chart_requirement(item)
        for item in _as_list(normalized.get("chart_requirements"))
        if isinstance(item, dict)
    ]

    confirmation_templates = normalized.get("static_confirmation_items")
    if confirmation_templates is None:
        confirmation_templates = normalized.get("confirmation_templates")
    normalized["static_confirmation_items"] = [
        _normalize_confirmation_template(item)
        for item in _as_list(confirmation_templates)
        if isinstance(item, dict)
    ]
    normalized.pop("confirmation_templates", None)
    return normalized


def _normalize_analysis_plan(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "analysis_block": str(item.get("analysis_block") or item.get("block") or "待确认"),
        "question": str(item.get("question") or item.get("goal") or ""),
        "support_status": str(item.get("support_status") or item.get("status") or "待确认"),
        "dependencies": str(item.get("dependencies") or item.get("dependency") or ""),
        "note": str(item.get("note") or item.get("reason") or ""),
    }


def _normalize_data_requirement(item: dict[str, Any]) -> dict[str, Any]:
    limitations = item.get("limitations")
    if isinstance(limitations, list):
        missing_impact = "；".join(str(x) for x in limitations if x)
    else:
        missing_impact = str(item.get("missing_impact") or item.get("impact") or "")

    return {
        "data_source": str(
            item.get("data_source") or item.get("module_name") or item.get("module_id") or "待确认"
        ),
        "field_or_sheet": str(item.get("field_or_sheet") or item.get("table_id") or item.get("source_table") or ""),
        "is_required": str(item.get("is_required") or item.get("required") or "建议"),
        "purpose": str(item.get("purpose") or item.get("reason") or ""),
        "missing_impact": missing_impact or "待确认",
        "current_note": str(item.get("current_note") or item.get("note") or ""),
        "module_id": str(item.get("module_id") or ""),
        "table_id": str(item.get("table_id") or ""),
        "planning_reason": str(item.get("planning_reason") or item.get("reason") or ""),
        "source_notes": str(item.get("source_notes") or ""),
    }


def _normalize_preprocess_step(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "step": str(item.get("step") or item.get("name") or "待确认"),
        "input_name": str(item.get("input_name") or item.get("input") or ""),
        "output_name": str(item.get("output_name") or item.get("output") or ""),
        "note": str(item.get("note") or item.get("reason") or ""),
    }


def _normalize_chart_requirement(item: dict[str, Any]) -> dict[str, Any]:
    chart_type = item.get("chart_type")
    chart_type = str(chart_type) if chart_type is not None else ""
    if chart_type not in VALID_CHART_TYPES:
        chart_type = None
    return {
        "chart_page": str(item.get("chart_page") or item.get("title") or item.get("chart_id") or "待确认"),
        "required_table": str(item.get("required_table") or item.get("table_id") or ""),
        "fields": str(item.get("fields") or ""),
        "status": str(item.get("status") or "待确认"),
        "note": str(item.get("note") or item.get("reason") or ""),
        "chart_type": chart_type,
        "data_module_id": str(item.get("data_module_id") or item.get("module_id") or ""),
        "table_ids": str(item.get("table_ids") or ""),
        "grain": str(item.get("grain") or ""),
        "metrics": str(item.get("metrics") or ""),
        "dimensions": str(item.get("dimensions") or ""),
        "planning_reason": str(item.get("planning_reason") or item.get("reason") or ""),
    }


def _normalize_confirmation_template(item: dict[str, Any]) -> dict[str, Any]:
    name = str(item.get("name") or item.get("item") or "待确认")
    return {
        "name": name,
        "question": str(item.get("question") or item.get("prompt") or ""),
        "suggested_value": str(item.get("suggested_value") or item.get("suggestion") or ""),
        "status": str(item.get("status") or "待确认"),
        "reason": str(item.get("reason") or item.get("note") or ""),
    }


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]
