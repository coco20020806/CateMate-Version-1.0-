"""Rule-based chart binding from workbook + plan + module contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from catemate.conclusion_brief.workbook_digest import (
    digest_table,
    load_json_model,
)
from catemate.html_report.contract_index import (
    ChartPreset,
    ModuleContractIndex,
    build_module_contract_index,
    lookup_preset,
)
from catemate.html_report.data_loader import (
    find_mom_y_fields,
    find_share_y_fields,
    infer_table_role,
    load_workbook_table_entries,
    repair_chart_binding,
    resolve_table_for_binding,
)
from catemate.html_report.schemas import ChartBinding, VisualReportSection
from catemate.orchestration.schemas import AnalysisPlan, ReportBlueprint, SolveVerdict


TIME_FIELDS = {"grass_month", "month", "year_month", "grass_date", "date"}
SITE_FIELDS = {"grass_region", "region", "site"}
METRIC_EXCLUDE = TIME_FIELDS | SITE_FIELDS


@dataclass
class TableRunMeta:
    table_id: str
    section_id: str
    module_id: str = ""
    metric_id: str = ""
    run_id: str = ""
    sheet_section_id: str = ""


@dataclass
class DraftBindingContext:
    original_question: str
    report_goal: str = ""
    bindings: list[ChartBinding] = field(default_factory=list)
    sections: list[VisualReportSection] = field(default_factory=list)
    unsolved_section_ids: set[str] = field(default_factory=set)
    table_columns: dict[str, list[str]] = field(default_factory=dict)


def _build_run_meta_map(plan: AnalysisPlan | None) -> dict[str, TableRunMeta]:
    meta: dict[str, TableRunMeta] = {}
    if plan is None:
        return meta
    for run in plan.runs:
        if not run.run_id:
            continue
        meta[run.run_id] = TableRunMeta(
            table_id=run.table_id,
            section_id=run.section_id,
            module_id=run.module_id,
            metric_id=run.metric_id,
            run_id=run.run_id,
        )
    return meta


def _pick_time_field(columns: list[str]) -> str | None:
    for name in columns:
        if name.strip().lower() in TIME_FIELDS:
            return name
    return None


def _pick_site_field(columns: list[str]) -> str | None:
    for name in columns:
        if name.strip().lower() in SITE_FIELDS:
            return name
    return None


def _pick_metric_fields(columns: list[str], preferred: list[str] | None = None) -> list[str]:
    if preferred:
        hits = [c for c in preferred if c in columns]
        if hits:
            return hits
    metrics = [
        c
        for c in columns
        if c.strip().lower() not in METRIC_EXCLUDE
        and not c.strip().lower().endswith("_pct")
        and "_mom_pct" not in c.strip().lower()
    ]
    return metrics[:3]


def _presentation_to_chart_type(presentation: str) -> str:
    text = (presentation or "").strip().lower()
    mapping = {
        "trend": "trend",
        "line": "trend",
        "bar": "bar",
        "share": "share",
        "pie": "share",
        "table": "table",
        "rank": "table",
    }
    return mapping.get(text, "table")


def _binding_from_preset(
    preset: ChartPreset,
    *,
    table_id: str,
    section_id: str,
    module_id: str,
    columns: list[str],
    table_id_hint: str,
) -> ChartBinding:
    chart_type_hint, role = infer_table_role(table_id_hint)
    chart_type = preset.suggested_chart_type if preset.suggested_chart_type != "table" else chart_type_hint
    if table_id_hint.endswith("_mom_by_site_month"):
        chart_type = "trend"
        role = "secondary"
    elif table_id_hint.endswith("_latest_month_pct_by_site"):
        chart_type = "share"
        role = "secondary"

    x_field = preset.x if preset.x in columns else _pick_time_field(columns) or _pick_site_field(columns)
    y_fields = [y for y in preset.y if y in columns]
    if not y_fields:
        if chart_type == "trend" and table_id_hint.endswith("_mom_by_site_month"):
            y_fields = find_mom_y_fields(columns)
        elif chart_type == "share":
            y_fields = find_share_y_fields(columns)
        else:
            y_fields = _pick_metric_fields(columns)

    series_field = preset.series if preset.series in columns else _pick_site_field(columns)
    title = preset.title_template or f"{table_id_hint}"
    return ChartBinding(
        chart_id=f"{section_id}_{table_id_hint}",
        section_id=section_id,
        table_id=table_id,
        module_id=module_id or preset.module_id,
        chart_type=chart_type,  # type: ignore[arg-type]
        title=title,
        x_field=x_field,
        y_fields=y_fields,
        series_field=series_field,
        role=role,  # type: ignore[arg-type]
        binding_source="chart_preset",
        confidence="high",
        notes=[f"Matched chart_preset {preset.preset_id}"],
    )


def _binding_from_heuristic(
    *,
    table_id: str,
    section_id: str,
    module_id: str,
    columns: list[str],
    digest: dict[str, Any],
    presentation: str = "",
) -> ChartBinding:
    table_kind = str(digest.get("table_kind") or "generic")
    chart_type_hint, role = infer_table_role(table_id)
    if table_kind in {"trend", "ranked", "share"}:
        chart_type_hint = table_kind if table_kind != "ranked" else "table"
        if table_kind == "share":
            chart_type_hint = "share"
    elif presentation and chart_type_hint == "table":
        chart_type_hint = _presentation_to_chart_type(presentation)

    if table_kind == "trend" or chart_type_hint == "trend":
        chart_type = "trend"
        x_field = _pick_time_field(columns)
        y_fields = _pick_metric_fields(columns)
        if table_id.endswith("_mom_by_site_month"):
            y_fields = find_mom_y_fields(columns) or y_fields
            role = "secondary"
        series_field = _pick_site_field(columns)
    elif table_kind == "share" or chart_type_hint == "share":
        chart_type = "share"
        x_field = _pick_site_field(columns)
        y_fields = find_share_y_fields(columns) or _pick_metric_fields(columns)
        series_field = None
        role = "secondary"
    elif table_kind == "ranked" or chart_type_hint == "table":
        chart_type = "table"
        x_field = None
        y_fields = _pick_metric_fields(columns)
        series_field = None
        top_n = 50
    else:
        chart_type = chart_type_hint
        x_field = _pick_time_field(columns) or _pick_site_field(columns)
        y_fields = _pick_metric_fields(columns)
        series_field = _pick_site_field(columns)
        top_n = 50 if chart_type == "table" else None

    confidence = "medium" if table_kind != "generic" else "low"
    return ChartBinding(
        chart_id=f"{section_id}_{table_id}",
        section_id=section_id,
        table_id=table_id,
        module_id=module_id,
        chart_type=chart_type,  # type: ignore[arg-type]
        title=table_id.replace("_", " "),
        x_field=x_field,
        y_fields=y_fields,
        series_field=series_field,
        top_n=top_n if chart_type == "table" else None,
        role=role,  # type: ignore[arg-type]
        binding_source="heuristic" if not presentation else "blueprint",
        confidence=confidence,  # type: ignore[arg-type]
        notes=[f"table_kind={table_kind}"],
    )


def _resolve_primary_roles(bindings: list[ChartBinding]) -> list[ChartBinding]:
    by_section: dict[str, list[ChartBinding]] = {}
    for binding in bindings:
        by_section.setdefault(binding.section_id, []).append(binding)

    resolved: list[ChartBinding] = []
    for section_id, items in by_section.items():
        primaries = [b for b in items if b.role == "primary"]
        if len(primaries) > 1:
            # Prefer trend > bar > table as primary
            priority = {"trend": 0, "bar": 1, "share": 2, "table": 3, "kpi_row": 4}
            items_sorted = sorted(items, key=lambda b: (priority.get(b.chart_type, 9), b.table_id))
            primary_id = items_sorted[0].chart_id
            for item in items:
                if item.chart_id == primary_id:
                    resolved.append(item.model_copy(update={"role": "primary"}))
                elif item.role == "primary":
                    resolved.append(item.model_copy(update={"role": "secondary"}))
                else:
                    resolved.append(item)
        else:
            resolved.extend(items)
    return resolved


def build_draft_bindings(
    *,
    workbook_path: Path,
    original_question: str,
    blueprint_path: Path | None = None,
    plan_path: Path | None = None,
    verdict_path: Path | None = None,
    contract_index: ModuleContractIndex | None = None,
) -> DraftBindingContext:
    entries = load_workbook_table_entries(workbook_path)
    blueprint = load_json_model(blueprint_path, ReportBlueprint)
    plan = load_json_model(plan_path, AnalysisPlan)
    verdict = load_json_model(verdict_path, SolveVerdict)
    index = contract_index or build_module_contract_index()

    run_meta = _build_run_meta_map(plan)
    presentation_by_section: dict[str, str] = {}
    title_by_section: dict[str, str] = {}
    sub_question_by_section: dict[str, str] = {}
    if blueprint is not None:
        for section in blueprint.sections:
            presentation_by_section[section.section_id] = section.expected_shape.presentation
            title_by_section[section.section_id] = section.title
            sub_question_by_section[section.section_id] = section.sub_question

    unsolved: set[str] = set()
    if verdict is not None:
        unsolved = {u.section_id for u in verdict.unsolved_sections}

    bindings: list[ChartBinding] = []
    table_columns: dict[str, list[str]] = {}

    for entry in entries:
        table_id = entry.table_id
        df = entry.df
        columns = [str(c) for c in df.columns]
        table_columns[table_id] = columns
        run = run_meta.get(entry.run_or_section)
        section_id = run.section_id if run is not None else entry.run_or_section
        module_id = run.module_id if run is not None else ""
        run_id = entry.run_or_section if run is not None else ""

        preset = lookup_preset(index, table_id=table_id, module_id=module_id)
        digest = digest_table(table_id, df, section_id=section_id, max_rows=5)

        if preset is not None:
            binding = _binding_from_preset(
                preset,
                table_id=table_id,
                section_id=section_id,
                module_id=module_id,
                columns=columns,
                table_id_hint=table_id,
            )
        else:
            binding = _binding_from_heuristic(
                table_id=table_id,
                section_id=section_id,
                module_id=module_id,
                columns=columns,
                digest=digest,
                presentation=presentation_by_section.get(section_id, ""),
            )

        binding = binding.model_copy(
            update={
                "chart_id": f"{section_id}_{run_id}_{table_id}" if run_id else f"{section_id}_{table_id}",
                "run_id": run_id,
                "sheet_name": entry.sheet_name,
            }
        )
        binding = repair_chart_binding(binding, df)

        if section_id in unsolved:
            binding = binding.model_copy(update={"visible": False, "confidence": "low"})
            binding.notes.append("Section marked unsolved in solve_verdict")

        bindings.append(binding)

    bindings = _resolve_primary_roles(bindings)

    section_ids: list[str] = []
    if blueprint is not None:
        section_ids = [s.section_id for s in blueprint.sections]
    else:
        seen: set[str] = set()
        for binding in bindings:
            if binding.section_id not in seen:
                section_ids.append(binding.section_id)
                seen.add(binding.section_id)

    sections: list[VisualReportSection] = []
    for section_id in section_ids:
        status = "unsolved" if section_id in unsolved else "solved"
        sections.append(
            VisualReportSection(
                section_id=section_id,
                title=title_by_section.get(section_id, section_id),
                sub_question=sub_question_by_section.get(section_id, ""),
                status=status,  # type: ignore[arg-type]
                charts=[b for b in bindings if b.section_id == section_id],
            )
        )

    # Orphan bindings not in blueprint sections
    known = set(section_ids)
    orphan_ids = sorted({b.section_id for b in bindings if b.section_id not in known})
    for section_id in orphan_ids:
        sections.append(
            VisualReportSection(
                section_id=section_id,
                title=section_id,
                status="partial",  # type: ignore[arg-type]
                charts=[b for b in bindings if b.section_id == section_id],
            )
        )

    report_goal = blueprint.goal if blueprint is not None else ""
    data_gaps = [f"{u.section_id}: {u.reason}" for u in verdict.unsolved_sections] if verdict else []

    return DraftBindingContext(
        original_question=original_question,
        report_goal=report_goal,
        bindings=bindings,
        sections=sections,
        unsolved_section_ids=unsolved,
        table_columns=table_columns,
    )


def draft_to_spec(draft: DraftBindingContext, *, case_id: str = "", generated_at: str = "") -> VisualReportSpec:
    from catemate.html_report.schemas import VisualReportSpec

    return VisualReportSpec(
        case_id=case_id,
        original_question=draft.original_question,
        report_goal=draft.report_goal,
        executive_summary="",
        sections=draft.sections,
        data_gaps=[
            f"{s.section_id} unresolved" for s in draft.sections if s.status == "unsolved"
        ],
        generated_at=generated_at,
        spec_status="draft",
    )
