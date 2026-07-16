"""Discover supported metrics per data module from contract.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from catemate.planning.context_loader import load_v2_data_module_contracts

METRIC_SOURCE_COLUMNS: dict[str, tuple[str, ...]] = {
    "gmv": ("gmv_usd",),
    "orders": ("orders",),
    "aov": ("gmv_usd", "orders"),
}


@lru_cache(maxsize=32)
def _contracts_by_module_id() -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for contract in load_v2_data_module_contracts():
        module_id = str(contract.get("module_id") or "").strip()
        if module_id:
            mapping[module_id] = contract
    return mapping


def list_module_metrics(module_id: str) -> list[str]:
    """Return metric_id values allowed by module contract."""
    contract = _contracts_by_module_id().get(module_id)
    if not contract:
        return []
    params = contract.get("compute_params") or {}
    metric_spec = params.get("metric_id") or {}
    allowed = metric_spec.get("allowed") or []
    return [str(item).strip() for item in allowed if str(item).strip()]


def filter_metrics_by_columns(metrics: list[str], columns: list[str]) -> list[str]:
    """Keep metrics whose required source columns are all present."""
    column_set = {str(col).strip() for col in columns}
    result: list[str] = []
    for metric_id in metrics:
        required = METRIC_SOURCE_COLUMNS.get(metric_id)
        if required is None:
            result.append(metric_id)
            continue
        if all(col in column_set for col in required):
            result.append(metric_id)
    return result


def available_metrics_for_module(module_id: str, columns: list[str]) -> list[str]:
    return filter_metrics_by_columns(list_module_metrics(module_id), columns)


def metric_key(section_id: str, metric_id: str) -> str:
    return f"{section_id}:{metric_id}"


def parse_metric_key(key: str) -> tuple[str, str]:
    section_id, metric_id = key.split(":", 1)
    return section_id, metric_id
