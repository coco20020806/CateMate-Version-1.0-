"""Resolve per-module rawdata source bindings from contract.yaml."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from catemate.data.rawdata_catalog import is_catalog_available
from catemate.planning.context_loader import load_v2_data_module_contracts


@lru_cache(maxsize=32)
def _contracts_by_module_id() -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for contract in load_v2_data_module_contracts():
        module_id = str(contract.get("module_id") or "").strip()
        if module_id:
            mapping[module_id] = contract
    return mapping


def get_source_bindings(module_id: str) -> dict[str, Any]:
    contract = _contracts_by_module_id().get(module_id) or {}
    bindings = contract.get("source_bindings") or {}
    return dict(bindings) if isinstance(bindings, dict) else {}


def allowed_grains(module_id: str) -> list[str]:
    bindings = get_source_bindings(module_id)
    grains = bindings.get("allowed_grains") or []
    return [str(item).strip() for item in grains if str(item).strip()]


def _grain_binding(module_id: str, grain: str) -> dict[str, Any]:
    bindings = get_source_bindings(module_id)
    by_grain = bindings.get("by_grain") or {}
    if not isinstance(by_grain, dict):
        return {}
    entry = by_grain.get(grain) or {}
    return dict(entry) if isinstance(entry, dict) else {}


def grain_candidates(module_id: str, grain: str) -> list[str]:
    entry = _grain_binding(module_id, grain)
    candidates = entry.get("candidates") or []
    default = str(entry.get("default_table_id") or "").strip()
    result: list[str] = []
    if default:
        result.append(default)
    for item in candidates:
        table_id = str(item).strip()
        if table_id and table_id not in result:
            result.append(table_id)
    return result


def grain_loader(module_id: str, grain: str) -> str:
    entry = _grain_binding(module_id, grain)
    return str(entry.get("loader") or "flat_workbook").strip() or "flat_workbook"


def grain_requires_scope(module_id: str, grain: str) -> list[str]:
    entry = _grain_binding(module_id, grain)
    required = entry.get("requires_scope") or []
    return [str(item).strip() for item in required if str(item).strip()]


def validate_run_source(module_id: str, grain: str, table_id: str) -> bool:
    if grain not in allowed_grains(module_id):
        return False
    candidates = grain_candidates(module_id, grain)
    if not candidates:
        return False
    return table_id in candidates


def resolve_table_id(
    module_id: str,
    grain: str,
    *,
    prefer: str = "",
    category_path: tuple[str, str, str] | None = None,
) -> str:
    if grain not in allowed_grains(module_id):
        raise ValueError(f"Module {module_id} does not allow grain={grain}")

    candidates = grain_candidates(module_id, grain)
    if not candidates:
        raise ValueError(f"Module {module_id} has no source candidates for grain={grain}")

    if prefer and prefer in candidates:
        return prefer

    for table_id in candidates:
        if is_catalog_available(grain, table_id, category_path=category_path):
            return table_id

    entry = _grain_binding(module_id, grain)
    default = str(entry.get("default_table_id") or "").strip()
    return default or candidates[0]
