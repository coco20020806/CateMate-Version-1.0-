"""Load active data modules for module selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from catemate.planning.context_loader import load_data_module_configs


def load_active_data_modules(data_modules_dir: Path) -> list[dict[str, Any]]:
    """Load active v2 data module YAML configs."""
    return load_data_module_configs(data_modules_dir, active_only=True)


def build_module_registry(modules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index modules by module_id."""
    registry: dict[str, dict[str, Any]] = {}
    for module in modules:
        module_id = str(module.get("module_id") or "").strip()
        if module_id:
            registry[module_id] = module
    return registry


def summarize_modules_for_selection(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact module summaries for AI module selection."""
    summaries: list[dict[str, Any]] = []
    for module in modules:
        if not isinstance(module, dict):
            continue
        business_purpose = module.get("business_purpose") or {}
        if not isinstance(business_purpose, dict):
            business_purpose = {}
        planning_hints = module.get("planning_hints") or {}
        if not isinstance(planning_hints, dict):
            planning_hints = {}
        lineage = module.get("lineage") or {}
        if not isinstance(lineage, dict):
            lineage = {}
        fields = module.get("fields") or {}
        if not isinstance(fields, dict):
            fields = {}

        summaries.append(
            {
                "module_id": module.get("module_id", ""),
                "module_name": module.get("module_name", ""),
                "module_type": module.get("module_type", ""),
                "description": business_purpose.get("description", ""),
                "typical_questions": business_purpose.get("typical_questions") or [],
                "not_suitable_for": business_purpose.get("not_suitable_for") or [],
                "use_when": planning_hints.get("use_when") or [],
                "avoid_when": planning_hints.get("avoid_when") or [],
                "explicit_triggers": planning_hints.get("explicit_triggers") or [],
                "preferred_over": planning_hints.get("preferred_over") or [],
                "can_combine_with": planning_hints.get("can_combine_with") or [],
                "source_tables": _extract_table_ids(module),
                "dimension_fields": [
                    item.get("field", "")
                    for item in (fields.get("dimensions") or [])
                    if isinstance(item, dict) and item.get("field")
                ],
                "metric_fields": [
                    item.get("field", "")
                    for item in (fields.get("metrics") or [])
                    if isinstance(item, dict) and item.get("field")
                ],
                "derived_metrics": [
                    item.get("metric_id", "")
                    for item in (module.get("derived_metrics") or [])
                    if isinstance(item, dict) and item.get("metric_id")
                ],
                "default_charts": module.get("default_charts") or [],
                "chart_rules": module.get("chart_rules") or {},
                "limitations": module.get("limitations") or [],
            }
        )
    return summaries


def _extract_table_ids(module: dict[str, Any]) -> list[str]:
    table_ids: list[str] = []
    lineage = module.get("lineage") or {}
    for container in (lineage, module):
        if not isinstance(container, dict):
            continue
        for item in container.get("source_tables") or []:
            if isinstance(item, dict) and item.get("table_id"):
                tid = str(item["table_id"])
                if tid not in table_ids:
                    table_ids.append(tid)
            elif isinstance(item, str) and item not in table_ids:
                table_ids.append(item)
    return table_ids
