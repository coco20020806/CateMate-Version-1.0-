"""Streamlit UI for category positioning confirmation gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import streamlit as st

from catemate.ai.client import CateMateAIClient
from catemate.ai.settings import AISettings
from catemate.pipeline.manifest import PipelineManifest, update_and_save_manifest
from catemate.understanding.category_confirmation import (
    apply_category_feedback,
    candidate_key,
    can_confirm_selection,
    confirm_categories,
    finalize_after_category_confirmation,
    is_category_confirmation_complete,
)
from catemate.understanding.clarification import normalize_clarifying_question_ids, save_understanding_spec
from catemate.understanding.schemas import RequirementUnderstandingSpec

POSITIONING_LABELS = {
    "single_category": "单类目",
    "multi_category": "多类目",
    "unresolved": "未决（请反馈或勾选 near-miss 候选）",
}


def load_understanding_spec(path: Path) -> RequirementUnderstandingSpec:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_clarifying_question_ids(RequirementUnderstandingSpec.model_validate(payload))


def _default_selected_paths(spec: RequirementUnderstandingSpec) -> set[str]:
    positioning = spec.understood.category_positioning
    if positioning.positioning_type == "single_category" and len(positioning.proposed_candidates) == 1:
        return {candidate_key(positioning.proposed_candidates[0])}
    return set()


def _selection_session_key(manifest_path: Path) -> str:
    return f"category_selection::{manifest_path}"


def render_category_confirmation_editor(
    understanding_spec_path: Path,
    manifest: PipelineManifest,
    manifest_path: Path,
    *,
    on_category_confirmed: Callable[[RequirementUnderstandingSpec], None] | None = None,
) -> tuple[RequirementUnderstandingSpec, bool]:
    """Render category confirmation UI. Returns (spec, is_complete)."""
    try:
        spec = load_understanding_spec(understanding_spec_path)
    except Exception as exc:
        st.error(f"读取 understanding spec 失败：{exc}")
        return RequirementUnderstandingSpec.model_construct(), False

    if is_category_confirmation_complete(spec):
        confirmed = spec.understood.category_positioning.confirmed_candidates
        if confirmed:
            st.success("类目已确认。")
            for item in confirmed:
                st.markdown(f"- `{candidate_key(item)}`（{item.confidence}）")
        else:
            st.success("类目已确认（legacy spec）。")
        return spec, True

    positioning = spec.understood.category_positioning
    proposed = positioning.proposed_candidates
    if not proposed:
        st.warning("当前没有可用的类目候选，请用自然语言描述你认为正确的类目。")
    else:
        label = POSITIONING_LABELS.get(positioning.positioning_type, positioning.positioning_type)
        st.markdown(f"**定位类型**：{label}")
        st.caption(f"共 {len(proposed)} 个候选；请勾选子集后点击【确认类目】（至少 1 项）。")

    selection_key = _selection_session_key(manifest_path)
    if selection_key not in st.session_state:
        st.session_state[selection_key] = list(_default_selected_paths(spec))

    selected_paths: list[str] = []
    for index, candidate in enumerate(proposed):
        path = candidate_key(candidate)
        checked = st.checkbox(
            f"`{path}` — {candidate.reason}（置信度：{candidate.confidence}）",
            value=path in st.session_state[selection_key],
            key=f"cat_cb::{manifest_path}::{index}",
        )
        if checked:
            selected_paths.append(path)
    st.session_state[selection_key] = selected_paths

    for round_item in positioning.feedback_rounds:
        with st.expander(f"反馈：{round_item.user_feedback[:40]}…", expanded=False):
            st.markdown(round_item.user_feedback)
            if round_item.system_summary:
                st.caption(round_item.system_summary)

    feedback_key = f"category_feedback::{manifest_path}"
    feedback_text = st.text_area(
        "自然语言反馈（可选）",
        placeholder="例如：应该是 Pet Accessories 下的 Bowls & Feeders，不是 Pet Food。",
        key=feedback_key,
    )

    col_feedback, col_confirm = st.columns(2)
    with col_feedback:
        if st.button("提交反馈", key=f"submit_category_feedback::{manifest_path}"):
            if not feedback_text.strip():
                st.warning("请先输入反馈内容。")
            else:
                try:
                    client = CateMateAIClient(AISettings.from_env())
                    updated = apply_category_feedback(spec, feedback_text.strip(), ai_client=client)
                    save_understanding_spec(updated, understanding_spec_path)
                    st.session_state.pop(selection_key, None)
                    st.rerun()
                except Exception as exc:
                    st.error(f"反馈处理失败：{exc}")

    with col_confirm:
        confirm_disabled = not can_confirm_selection(selected_paths)
        if st.button(
            "确认类目",
            type="primary",
            disabled=confirm_disabled,
            key=f"confirm_category::{manifest_path}",
        ):
            try:
                client = CateMateAIClient(AISettings.from_env())
                updated = confirm_categories(spec, selected_paths)
                updated = finalize_after_category_confirmation(updated, ai_client=client)
                save_understanding_spec(updated, understanding_spec_path)
                update_and_save_manifest(
                    manifest_path=manifest_path,
                    case_id=manifest.case_id,
                    timestamp=manifest.timestamp,
                    request_text=manifest.request_text,
                    provider=manifest.provider,
                    model=manifest.model,
                    planning_mode=manifest.planning_mode,
                    case_config_path=manifest.case_config_path,
                    understanding_spec_path=str(understanding_spec_path),
                    status="category_confirmed",
                )
                if on_category_confirmed is not None:
                    on_category_confirmed(updated)
                st.rerun()
            except Exception as exc:
                st.error(f"确认类目失败：{exc}")

    if confirm_disabled:
        st.caption("请至少勾选 1 个类目候选后，才能点击【确认类目】。")

    return spec, False
