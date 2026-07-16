"""Build compressed module capability catalog for blueprint LLM prompts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from catemate.core.output_policy import enabled_module_ids
from catemate.core.paths import CONFIG_DIR, PROCESSED_DATA_DIR
from catemate.planning.context_loader import (
    DEFAULT_MANIFEST_PATH,
    load_processed_manifest,
    load_v2_data_module_contracts,
)

ANALYSIS_PLAYBOOK_PATH = CONFIG_DIR / "analysis_playbook.md"


def load_analysis_playbook(path: Path | None = None) -> str:
    playbook_path = path or ANALYSIS_PLAYBOOK_PATH
    if not playbook_path.exists():
        return ""
    return playbook_path.read_text(encoding="utf-8").strip()


def build_module_catalog_for_blueprint(
    *,
    include_manifest: bool = True,
    manifest_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Summarize V2 module contracts for blueprint generation."""
    manifest_table_ids: set[str] = set()
    if include_manifest:
        manifest_table_ids = _load_manifest_table_ids(manifest_path)

    allowed_ids = set(enabled_module_ids())
    catalog: list[dict[str, Any]] = []
    for contract in load_v2_data_module_contracts():
        module_id = str(contract.get("module_id") or "").strip()
        if allowed_ids and module_id not in allowed_ids:
            continue
        entry = _summarize_contract(contract)
        if manifest_table_ids and entry.get("source_table_ids"):
            available = [tid for tid in entry["source_table_ids"] if tid in manifest_table_ids]
            entry["available_source_tables"] = available
        catalog.append(entry)
    return catalog


def _load_manifest_table_ids(manifest_path: Path | None) -> set[str]:
    path = manifest_path or DEFAULT_MANIFEST_PATH
    if not path.exists():
        fallback = PROCESSED_DATA_DIR / "processed_manifest.yaml"
        if fallback.exists():
            path = fallback
        else:
            return set()
    try:
        manifest = load_processed_manifest(path)
    except (FileNotFoundError, ValueError):
        return set()
    table_ids: set[str] = set()
    for table in manifest.get("tables") or []:
        if isinstance(table, dict) and table.get("table_id"):
            table_ids.add(str(table["table_id"]))
    return table_ids


def _summarize_contract(contract: dict[str, Any]) -> dict[str, Any]:
    module_id = str(contract.get("module_id") or "").strip()
    business_purpose = contract.get("business_purpose") or {}
    if not isinstance(business_purpose, dict):
        business_purpose = {}

    source_bindings = contract.get("source_bindings") or {}
    allowed_grains = source_bindings.get("allowed_grains") or []
    if not isinstance(allowed_grains, list):
        allowed_grains = []

    compute_params = contract.get("compute_params") or {}
    metric_spec = compute_params.get("metric_id") or {}
    allowed_metrics = metric_spec.get("allowed") or []
    if not isinstance(allowed_metrics, list):
        allowed_metrics = []

    sort_by_spec = compute_params.get("sort_by") or {}
    sort_by_allowed = sort_by_spec.get("allowed") or []
    if isinstance(sort_by_allowed, list) and sort_by_allowed:
        for item in sort_by_allowed:
            if item == "both":
                continue
            if str(item) not in allowed_metrics:
                allowed_metrics.append(str(item))

    if not allowed_metrics and module_id in {"top_shop", "top_listing", "price_tier_distribution", "keywords"}:
        allowed_metrics = _default_metrics_for_module(module_id)

    output_grains = _collect_output_grains(contract)
    source_table_ids = _collect_source_table_ids(source_bindings)
    planning_hints = contract.get("planning_hints") or {}
    if not isinstance(planning_hints, dict):
        planning_hints = {}

    limitations = contract.get("limitations") or []
    not_suitable = business_purpose.get("not_suitable_for") or []
    if not isinstance(not_suitable, list):
        not_suitable = []

    entry: dict[str, Any] = {
        "module_id": module_id,
        "module_name": contract.get("module_name") or module_id,
        "description": business_purpose.get("description") or "",
        "allowed_grains": [str(g) for g in allowed_grains],
        "allowed_metrics": [str(m) for m in allowed_metrics],
        "typical_questions": business_purpose.get("typical_questions") or [],
        "not_suitable_for": not_suitable,
        "limitations": limitations if isinstance(limitations, list) else [],
        "output_grains": output_grains,
        "source_table_ids": source_table_ids,
    }

    for hint_key in ("use_when", "avoid_when", "explicit_triggers"):
        hint_value = planning_hints.get(hint_key)
        if hint_value:
            entry[hint_key] = hint_value

    return entry


def _default_metrics_for_module(module_id: str) -> list[str]:
    defaults = {
        "top_shop": ["gmv"],
        "top_listing": ["gmv"],
        "price_tier_distribution": ["gmv"],
        "keywords": ["clicks"],
    }
    return list(defaults.get(module_id, []))


def _collect_output_grains(contract: dict[str, Any]) -> list[str]:
    grains: list[str] = []
    outputs = contract.get("outputs") or {}
    for bucket_key in ("primary", "derived"):
        for output in outputs.get(bucket_key) or []:
            if not isinstance(output, dict):
                continue
            for grain in output.get("grain") or []:
                grain_text = str(grain).strip()
                if grain_text and grain_text not in grains:
                    grains.append(grain_text)
    return grains


def _collect_source_table_ids(source_bindings: dict[str, Any]) -> list[str]:
    table_ids: list[str] = []
    by_grain = source_bindings.get("by_grain") or {}
    if not isinstance(by_grain, dict):
        return table_ids
    for binding in by_grain.values():
        if not isinstance(binding, dict):
            continue
        for key in ("default_table_id",):
            value = binding.get(key)
            if value and str(value) not in table_ids:
                table_ids.append(str(value))
        for candidate in binding.get("candidates") or []:
            candidate_text = str(candidate).strip()
            if candidate_text and candidate_text not in table_ids:
                table_ids.append(candidate_text)
    return table_ids
