"""Generate conclusion brief from V2 Data Workbook via LLM."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from typing import Any

from pydantic import ValidationError

from catemate.ai.client import CateMateAIClient
from catemate.ai.settings import AISettings
from catemate.conclusion_brief.brief_number_approximator import apply_number_approximation
from catemate.conclusion_brief.markdown_renderer import render_conclusion_brief_markdown
from catemate.conclusion_brief.prompt_builder import build_conclusion_brief_messages
from catemate.conclusion_brief.schemas import ConclusionBrief
from catemate.conclusion_brief.workbook_digest import build_workbook_digest, digest_to_payload
from catemate.pipeline.manifest import utc_now_iso


@dataclass
class ConclusionBriefOutputs:
    case_id: str
    json_path: Path
    md_path: Path


def _default_output_paths(
    *,
    workbook_path: Path,
    case_id: str,
    timestamp: str,
    json_output: Path | None,
    md_output: Path | None,
) -> tuple[Path, Path]:
    stem = f"conclusion_brief_{case_id}_{timestamp}" if case_id and timestamp else f"conclusion_brief_{workbook_path.stem}"
    json_path = json_output or workbook_path.with_name(f"{stem}.json")
    md_path = md_output or workbook_path.with_name(f"{stem}.md")
    return json_path, md_path


def _stringify_item(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        parts = [str(v).strip() for v in item.values() if v]
        return " — ".join(p for p in parts if p)
    return str(item).strip()


def normalize_conclusion_brief_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce common LLM shape drift before Pydantic validation."""
    normalized = dict(raw)
    for key in ("data_gaps", "caveats", "cross_cutting_insights"):
        items = normalized.get(key)
        if not isinstance(items, list):
            continue
        normalized[key] = [_stringify_item(item) for item in items if _stringify_item(item)]
    return normalized


def generate_conclusion_brief(
    *,
    workbook_path: Path,
    original_question: str,
    blueprint_path: Path | None = None,
    plan_path: Path | None = None,
    verdict_path: Path | None = None,
    json_output: Path | None = None,
    md_output: Path | None = None,
    case_id: str = "",
    timestamp: str = "",
    max_tables: int = 30,
    max_rows_per_table: int = 10,
    ai_client: CateMateAIClient | None = None,
) -> ConclusionBrief:
    digest_ctx = build_workbook_digest(
        workbook_path=workbook_path,
        original_question=original_question,
        blueprint_path=blueprint_path,
        plan_path=plan_path,
        verdict_path=verdict_path,
        max_tables=max_tables,
        max_rows_per_table=max_rows_per_table,
    )
    payload = digest_to_payload(digest_ctx)
    messages = build_conclusion_brief_messages(payload)

    client = ai_client
    if client is None:
        client = CateMateAIClient(AISettings.from_env())

    raw = client.complete_json(messages)
    raw = normalize_conclusion_brief_raw(raw)
    try:
        brief = ConclusionBrief.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"LLM returned invalid ConclusionBrief JSON: {exc}") from exc

    if not brief.generated_at:
        brief = brief.model_copy(update={"generated_at": utc_now_iso()})
    if not brief.original_question:
        brief = brief.model_copy(update={"original_question": original_question})
    if digest_ctx.blueprint and not brief.report_goal:
        brief = brief.model_copy(update={"report_goal": digest_ctx.blueprint.goal})

    brief = apply_number_approximation(brief)

    json_path, md_path = _default_output_paths(
        workbook_path=workbook_path,
        case_id=case_id,
        timestamp=timestamp,
        json_output=json_output,
        md_output=md_output,
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(brief.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(render_conclusion_brief_markdown(brief), encoding="utf-8")
    return brief


def build_conclusion_brief_outputs(
    *,
    workbook_path: Path,
    original_question: str,
    blueprint_path: Path | None = None,
    plan_path: Path | None = None,
    verdict_path: Path | None = None,
    json_output: Path | None = None,
    md_output: Path | None = None,
    case_id: str = "",
    timestamp: str = "",
    max_tables: int = 30,
    max_rows_per_table: int = 10,
    ai_client: CateMateAIClient | None = None,
) -> ConclusionBriefOutputs:
    generate_conclusion_brief(
        workbook_path=workbook_path,
        original_question=original_question,
        blueprint_path=blueprint_path,
        plan_path=plan_path,
        verdict_path=verdict_path,
        json_output=json_output,
        md_output=md_output,
        case_id=case_id,
        timestamp=timestamp,
        max_tables=max_tables,
        max_rows_per_table=max_rows_per_table,
        ai_client=ai_client,
    )
    json_path, md_path = _default_output_paths(
        workbook_path=workbook_path,
        case_id=case_id,
        timestamp=timestamp,
        json_output=json_output,
        md_output=md_output,
    )
    return ConclusionBriefOutputs(case_id=case_id, json_path=json_path, md_path=md_path)
