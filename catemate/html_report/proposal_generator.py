"""LLM proposal generator for VisualReportSpec."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from catemate.ai.client import CateMateAIClient
from catemate.ai.settings import AISettings
from catemate.conclusion_brief.schemas import ConclusionBrief
from catemate.conclusion_brief.workbook_digest import build_workbook_digest, digest_to_payload, load_json_model
from catemate.html_report.binder import DraftBindingContext, build_draft_bindings, draft_to_spec
from catemate.html_report.contract_index import build_module_contract_index
from catemate.html_report.data_loader import (
    load_workbook_table_entries,
    repair_chart_binding,
    resolve_table_for_binding,
)
from catemate.html_report.prompt_builder import build_visual_report_messages
from catemate.html_report.schemas import ChartBinding, VisualReportSection, VisualReportSpec
from catemate.pipeline.manifest import utc_now_iso


def _binding_to_dict(binding: ChartBinding) -> dict[str, Any]:
    return binding.model_dump(mode="json")


def _section_to_dict(section: VisualReportSection) -> dict[str, Any]:
    return section.model_dump(mode="json")


def build_proposal_payload(
    *,
    draft: DraftBindingContext,
    digest_payload: dict[str, Any],
    contract_index_payload: dict[str, Any],
    conclusion_brief: ConclusionBrief | None = None,
) -> dict[str, Any]:
    payload = {
        "original_question": draft.original_question,
        "report_goal": draft.report_goal,
        "digest": digest_payload,
        "rule_bindings": [_binding_to_dict(b) for b in draft.bindings],
        "rule_sections": [_section_to_dict(s) for s in draft.sections],
        "table_columns": draft.table_columns,
        "unsolved_section_ids": sorted(draft.unsolved_section_ids),
        "chart_preset_candidates": contract_index_payload,
    }
    if conclusion_brief is not None:
        payload["conclusion_brief"] = conclusion_brief.model_dump(mode="json")
    return payload


def _contract_index_payload() -> dict[str, Any]:
    index = build_module_contract_index()
    by_module: dict[str, list[dict[str, Any]]] = {}
    for module_id, presets in index.presets_by_module.items():
        by_module[module_id] = [
            {
                "preset_id": p.preset_id,
                "output_table_id": p.output_table_id,
                "suggested_chart_type": p.suggested_chart_type,
                "x": p.x,
                "y": p.y,
                "series": p.series,
            }
            for p in presets
        ]
    return by_module


def _validate_and_repair_spec(
    spec: VisualReportSpec,
    *,
    workbook_path: Path,
    draft: DraftBindingContext,
) -> VisualReportSpec:
    entries = load_workbook_table_entries(workbook_path)
    draft_by_key = {(binding.section_id, binding.table_id): binding for binding in draft.bindings}

    sections: list[VisualReportSection] = []
    for section in spec.sections:
        charts: list[ChartBinding] = []
        for chart in section.charts:
            draft_binding = draft_by_key.get((section.section_id, chart.table_id))
            run_id = chart.run_id or (draft_binding.run_id if draft_binding else "")
            sheet_name = chart.sheet_name or (draft_binding.sheet_name if draft_binding else "")
            entry = resolve_table_for_binding(
                entries,
                table_id=chart.table_id,
                run_id=run_id,
                section_id=section.section_id,
                sheet_name=sheet_name,
            )
            if entry is None and draft_binding is not None:
                entry = resolve_table_for_binding(
                    entries,
                    table_id=draft_binding.table_id,
                    run_id=draft_binding.run_id,
                    section_id=draft_binding.section_id,
                    sheet_name=draft_binding.sheet_name,
                )
            if entry is None:
                charts.append(chart.model_copy(update={"visible": False, "confidence": "low"}))
                continue
            repaired = repair_chart_binding(chart, entry.df)
            if draft_binding is not None:
                repaired = repaired.model_copy(
                    update={
                        "run_id": draft_binding.run_id,
                        "sheet_name": draft_binding.sheet_name,
                        "table_id": draft_binding.table_id,
                    }
                )
            charts.append(repaired)
        sections.append(section.model_copy(update={"charts": charts}))
    return spec.model_copy(update={"sections": sections})


def normalize_visual_report_raw(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(raw)
    for key in ("data_gaps",):
        items = normalized.get(key)
        if isinstance(items, list):
            normalized[key] = [str(item).strip() for item in items if str(item).strip()]
    return normalized


def propose_visual_report_spec(
    *,
    workbook_path: Path,
    original_question: str,
    case_id: str = "",
    blueprint_path: Path | None = None,
    plan_path: Path | None = None,
    verdict_path: Path | None = None,
    conclusion_brief_path: Path | None = None,
    max_tables: int = 30,
    max_rows_per_table: int = 10,
    ai_client: CateMateAIClient | None = None,
) -> VisualReportSpec:
    draft = build_draft_bindings(
        workbook_path=workbook_path,
        original_question=original_question,
        blueprint_path=blueprint_path,
        plan_path=plan_path,
        verdict_path=verdict_path,
    )
    digest_ctx = build_workbook_digest(
        workbook_path=workbook_path,
        original_question=original_question,
        blueprint_path=blueprint_path,
        plan_path=plan_path,
        verdict_path=verdict_path,
        max_tables=max_tables,
        max_rows_per_table=max_rows_per_table,
    )
    digest_payload = digest_to_payload(digest_ctx)
    conclusion_brief = load_json_model(conclusion_brief_path, ConclusionBrief)
    payload = build_proposal_payload(
        draft=draft,
        digest_payload=digest_payload,
        contract_index_payload=_contract_index_payload(),
        conclusion_brief=conclusion_brief,
    )
    messages = build_visual_report_messages(payload)

    client = ai_client
    if client is None:
        client = CateMateAIClient(AISettings.from_env())

    try:
        raw = client.complete_json(messages)
        raw = normalize_visual_report_raw(raw)
        spec = VisualReportSpec.model_validate(raw)
    except (ValidationError, ValueError, RuntimeError):
        spec = draft_to_spec(draft, case_id=case_id, generated_at=utc_now_iso())
        if conclusion_brief is not None:
            spec = _merge_conclusion_brief(spec, conclusion_brief)
        return _validate_and_repair_spec(spec, workbook_path=workbook_path, draft=draft)

    if not spec.case_id:
        spec = spec.model_copy(update={"case_id": case_id})
    if not spec.original_question:
        spec = spec.model_copy(update={"original_question": original_question})
    if not spec.report_goal and draft.report_goal:
        spec = spec.model_copy(update={"report_goal": draft.report_goal})
    if not spec.generated_at:
        spec = spec.model_copy(update={"generated_at": utc_now_iso()})
    spec = spec.model_copy(update={"spec_status": "draft"})
    if conclusion_brief is not None:
        spec = _merge_conclusion_brief(spec, conclusion_brief)
    return _validate_and_repair_spec(spec, workbook_path=workbook_path, draft=draft)


def _merge_conclusion_brief(spec: VisualReportSpec, brief: ConclusionBrief) -> VisualReportSpec:
    brief_by_section = {s.section_id: s for s in brief.sections}
    sections: list[VisualReportSection] = []
    for section in spec.sections:
        brief_section = brief_by_section.get(section.section_id)
        if brief_section is None:
            sections.append(section)
            continue
        narrative = section.narrative or brief_section.direct_answer
        sections.append(
            section.model_copy(
                update={
                    "title": section.title or brief_section.title,
                    "sub_question": section.sub_question or brief_section.sub_question,
                    "narrative": narrative,
                }
            )
        )
    executive = spec.executive_summary or brief.executive_summary
    data_gaps = list(spec.data_gaps)
    for gap in brief.data_gaps:
        if gap not in data_gaps:
            data_gaps.append(gap)
    return spec.model_copy(
        update={
            "executive_summary": executive,
            "report_goal": spec.report_goal or brief.report_goal,
            "sections": sections,
            "data_gaps": data_gaps,
        }
    )


def load_visual_report_spec(path: Path) -> VisualReportSpec:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return VisualReportSpec.model_validate(payload)


def save_visual_report_spec(spec: VisualReportSpec, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(spec.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
