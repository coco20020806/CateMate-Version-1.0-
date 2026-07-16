"""Streamlit UI for answering or skipping requirement clarifying questions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import streamlit as st

from catemate.pipeline.manifest import PipelineManifest, update_and_save_manifest
from catemate.understanding.clarification import (
    SKIPPED_ANSWER,
    apply_clarification_answer,
    is_clarification_complete,
    normalize_clarifying_question_ids,
    save_understanding_spec,
    unanswered_clarifying_questions,
)
from catemate.understanding.schemas import QuestionCategory, QuestionType, RequirementUnderstandingSpec


def load_understanding_spec(path: Path) -> RequirementUnderstandingSpec:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_clarifying_question_ids(RequirementUnderstandingSpec.model_validate(payload))


def render_clarification_editor(
    understanding_spec_path: Path,
    manifest: PipelineManifest,
    manifest_path: Path,
    *,
    on_clarification_complete: Callable[[RequirementUnderstandingSpec], None] | None = None,
) -> tuple[RequirementUnderstandingSpec, bool]:
    """Render per-question answer/skip UI. Returns (spec, is_complete)."""
    try:
        spec = load_understanding_spec(understanding_spec_path)
    except Exception as exc:
        st.error(f"读取 understanding spec 失败：{exc}")
        return RequirementUnderstandingSpec.model_construct(), False

    pending = unanswered_clarifying_questions(spec)
    if not spec.clarifying_questions:
        st.info("当前理解结果没有需要澄清的问题，可直接继续后续步骤。")
        return spec, True

    if not pending:
        st.success("所有澄清问题已处理完毕。")
        return spec, True

    st.caption(f"还有 {len(pending)} 条澄清问题待处理。请逐条自然语言回答，或选择跳过（将记录默认假设）。")

    business_pending = [
        q for q in pending if q.question_category == QuestionCategory.CLARIFY_BUSINESS
    ]
    rawdata_pending = [q for q in pending if q.question_category == QuestionCategory.RAWDATA]

    if business_pending:
        st.markdown("#### 业务澄清")
    for question in business_pending:
        _render_question_editor(
            question,
            understanding_spec_path=understanding_spec_path,
            manifest=manifest,
            manifest_path=manifest_path,
            on_clarification_complete=on_clarification_complete,
        )

    if rawdata_pending:
        st.markdown("#### 数据补充（请粘贴文件完整路径）")
    for question in rawdata_pending:
        _render_question_editor(
            question,
            understanding_spec_path=understanding_spec_path,
            manifest=manifest,
            manifest_path=manifest_path,
            on_clarification_complete=on_clarification_complete,
            is_file_path=True,
        )

    if is_clarification_complete(spec):
        _update_manifest_clarification_status(manifest, manifest_path, spec, complete=True)
        return spec, True

    return spec, False


def _render_question_editor(
    question,
    *,
    understanding_spec_path: Path,
    manifest: PipelineManifest,
    manifest_path: Path,
    on_clarification_complete,
    is_file_path: bool = False,
) -> None:
    with st.container(border=True):
        st.markdown(f"**{question.question}**")
        if question.reason:
            st.caption(question.reason)
        if question.default_assumption:
            st.caption(f"跳过默认假设：{question.default_assumption}")

        answer_key = f"clarify_answer::{understanding_spec_path}::{question.question_id}"
        use_file_path = is_file_path or question.expected_answer_type == QuestionType.FILE_PATH
        answer_text = st.text_input(
            "文件完整路径" if use_file_path else "自然语言回答",
            key=answer_key,
            placeholder="例如 C:\\data\\shop_sales.xlsx" if use_file_path else "请输入你的回答；若选择跳过可留空。",
        )

        col_answer, col_skip = st.columns(2)
        with col_answer:
            if st.button(
                "提交回答",
                key=f"clarify_submit::{question.question_id}",
                type="primary",
                disabled=not answer_text.strip(),
            ):
                try:
                    spec = load_understanding_spec(understanding_spec_path)
                    if use_file_path and question.rawdata_grain and question.rawdata_table_id:
                        from catemate.data.rawdata_ingest import ingest_rawdata_from_path

                        ingest_rawdata_from_path(
                            source_path=answer_text.strip(),
                            grain=question.rawdata_grain,
                            table_id=question.rawdata_table_id,
                        )
                    spec = apply_clarification_answer(
                        spec,
                        question.question_id,
                        answer_text=answer_text,
                        skipped=False,
                    )
                    save_understanding_spec(spec, understanding_spec_path)
                    if on_clarification_complete is not None:
                        on_clarification_complete(spec)
                    st.rerun()
                except Exception as exc:
                    st.error(f"保存回答失败：{exc}")

        with col_skip:
            if st.button("跳过", key=f"clarify_skip::{question.question_id}"):
                try:
                    spec = load_understanding_spec(understanding_spec_path)
                    spec = apply_clarification_answer(
                        spec,
                        question.question_id,
                        skipped=True,
                    )
                    save_understanding_spec(spec, understanding_spec_path)
                    if on_clarification_complete is not None:
                        on_clarification_complete(spec)
                    st.rerun()
                except Exception as exc:
                    st.error(f"跳过失败：{exc}")


def mark_clarification_completed(manifest: PipelineManifest, manifest_path: Path) -> None:
    """Update manifest status after all clarifying questions are handled."""
    from catemate.core.paths import PROJECT_ROOT
    from catemate.pipeline.manifest import resolve_manifest_path

    update_and_save_manifest(
        manifest_path=manifest_path,
        case_id=manifest.case_id,
        timestamp=manifest.timestamp,
        request_text=manifest.request_text,
        provider=manifest.provider,
        model=manifest.model,
        planning_mode=manifest.planning_mode,
        case_config_path=resolve_manifest_path(PROJECT_ROOT, manifest.case_config_path),
        understanding_spec_path=resolve_manifest_path(PROJECT_ROOT, manifest.understanding_spec_path),
        module_selection_plan_path=resolve_manifest_path(PROJECT_ROOT, manifest.module_selection_plan_path),
        planning_spec_path=resolve_manifest_path(PROJECT_ROOT, manifest.planning_spec_path),
        requirement_workbook_path=resolve_manifest_path(PROJECT_ROOT, manifest.requirement_workbook_path),
        ppt_ready_workbook_path=resolve_manifest_path(PROJECT_ROOT, manifest.ppt_ready_workbook_path),
        html_preview_path=resolve_manifest_path(PROJECT_ROOT, manifest.html_preview_path),
        status="clarification_completed",
    )


def _update_manifest_clarification_status(
    manifest: PipelineManifest,
    manifest_path: Path,
    spec: RequirementUnderstandingSpec,
    *,
    complete: bool,
) -> None:
    if complete:
        mark_clarification_completed(manifest, manifest_path)


def render_answered_clarifications(spec: RequirementUnderstandingSpec) -> None:
    if not spec.user_answers:
        return
    with st.expander(f"已处理澄清（{len(spec.user_answers)}）", expanded=False):
        for answer in spec.user_answers:
            question = next(
                (item for item in spec.clarifying_questions if item.question_id == answer.question_id),
                None,
            )
            label = question.question if question else answer.question_id
            if answer.answer == SKIPPED_ANSWER:
                st.markdown(f"- **{label}**：已跳过")
            else:
                st.markdown(f"- **{label}**：{answer.answer}")
