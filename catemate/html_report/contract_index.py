"""Index chart_presets from data_modules/*/contract.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from catemate.planning.context_loader import load_v2_data_module_contracts


@dataclass
class ChartPreset:
    preset_id: str
    module_id: str
    output_table_id: str
    suggested_chart_type: str
    x: str | None = None
    y: list[str] = field(default_factory=list)
    series: str | None = None
    metric_id: str = ""
    binding: str = "soft"
    title_template: str = ""


@dataclass
class ModuleContractIndex:
    presets_by_table: dict[str, list[ChartPreset]] = field(default_factory=dict)
    presets_by_module: dict[str, list[ChartPreset]] = field(default_factory=dict)
    module_names: dict[str, str] = field(default_factory=dict)


def _normalize_chart_type(raw: str) -> str:
    text = (raw or "").strip().lower()
    if text in {"auto_by_month_count", "auto"}:
        return "trend"
    if text in {"trend", "bar", "share", "table", "kpi_row"}:
        return text
    return "table"


def _parse_preset(module_id: str, payload: dict[str, Any]) -> ChartPreset | None:
    table_id = str(payload.get("output_table_id") or "").strip()
    if not table_id:
        return None
    y_raw = payload.get("y") or payload.get("y_axis") or []
    if isinstance(y_raw, str):
        y_fields = [y_raw]
    elif isinstance(y_raw, list):
        y_fields = [str(v) for v in y_raw if v]
    else:
        y_fields = []
    x_raw = payload.get("x") or payload.get("x_axis")
    series_raw = payload.get("series")
    return ChartPreset(
        preset_id=str(payload.get("preset_id") or payload.get("chart_intent") or table_id),
        module_id=module_id,
        output_table_id=table_id,
        suggested_chart_type=_normalize_chart_type(str(payload.get("suggested_chart_type") or payload.get("default_chart_type") or "table")),
        x=str(x_raw).strip() if x_raw else None,
        y=y_fields,
        series=str(series_raw).strip() if series_raw else None,
        metric_id=str(payload.get("metric_id") or ""),
        binding=str(payload.get("binding") or "soft"),
        title_template=str(payload.get("title_template") or payload.get("title") or ""),
    )


def build_module_contract_index(*, active_only: bool = True) -> ModuleContractIndex:
    index = ModuleContractIndex()
    for contract in load_v2_data_module_contracts(active_only=active_only):
        module_id = str(contract.get("module_id") or "").strip()
        if not module_id:
            continue
        index.module_names[module_id] = str(contract.get("module_name") or module_id)
        presets_raw = contract.get("chart_presets") or contract.get("default_charts") or []
        if not isinstance(presets_raw, list):
            continue
        for item in presets_raw:
            if not isinstance(item, dict):
                continue
            preset = _parse_preset(module_id, item)
            if preset is None:
                continue
            index.presets_by_table.setdefault(preset.output_table_id, []).append(preset)
            index.presets_by_module.setdefault(module_id, []).append(preset)
    return index


def lookup_preset(
    index: ModuleContractIndex,
    *,
    table_id: str,
    module_id: str = "",
) -> ChartPreset | None:
    candidates = index.presets_by_table.get(table_id) or []
    if module_id:
        for preset in candidates:
            if preset.module_id == module_id:
                return preset
    return candidates[0] if candidates else None
