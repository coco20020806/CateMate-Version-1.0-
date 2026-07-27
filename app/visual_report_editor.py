"""Streamlit UI for VisualReportSpec Gate C review."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from catemate.html_report.proposal_generator import load_visual_report_spec, save_visual_report_spec
from catemate.html_report.schemas import ChartBinding, VisualReportSection, VisualReportSpec

CHART_TYPES = ["trend", "bar", "share", "table", "kpi_row"]
ROLES = ["primary", "secondary"]


def spec_session_key(spec_path: Path) -> str:
    return f"visual_report_spec::{spec_path.resolve()}"


def load_spec_state(spec_path: Path) -> VisualReportSpec:
    key = spec_session_key(spec_path)
    if key not in st.session_state:
        st.session_state[key] = load_visual_report_spec(spec_path).model_dump(mode="json")
    return VisualReportSpec.model_validate(st.session_state[key])


def save_spec_state(spec_path: Path, spec: VisualReportSpec) -> None:
    st.session_state[spec_session_key(spec_path)] = spec.model_dump(mode="json")


def render_chart_editor(
    *,
    spec_path: Path,
    section_index: int,
    chart_index: int,
    chart: ChartBinding,
) -> ChartBinding:
    prefix = f"vr_{section_index}_{chart_index}"
    col1, col2 = st.columns([3, 1])
    with col1:
        title = st.text_input("标题", value=chart.title, key=f"{prefix}_title")
    with col2:
        visible = st.checkbox("展示", value=chart.visible, key=f"{prefix}_visible")

    col3, col4, col5 = st.columns(3)
    with col3:
        chart_type = st.selectbox(
            "图表类型",
            CHART_TYPES,
            index=CHART_TYPES.index(chart.chart_type) if chart.chart_type in CHART_TYPES else 0,
            key=f"{prefix}_type",
        )
    with col4:
        role = st.selectbox(
            "角色",
            ROLES,
            index=ROLES.index(chart.role) if chart.role in ROLES else 0,
            key=f"{prefix}_role",
        )
    with col5:
        st.caption(f"来源: {chart.binding_source}")
        st.caption(f"置信度: {chart.confidence}")

    st.caption(f"table_id: `{chart.table_id}` | x: `{chart.x_field}` | y: {chart.y_fields}")
    if chart.notes:
        st.caption("notes: " + " | ".join(chart.notes))

    return chart.model_copy(
        update={
            "title": title,
            "visible": visible,
            "chart_type": chart_type,  # type: ignore[arg-type]
            "role": role,  # type: ignore[arg-type]
        }
    )


def render_visual_report_editor(spec_path: Path) -> tuple[VisualReportSpec, bool]:
    """Render Gate C editor. Returns (spec, confirmed_clicked)."""
    spec = load_spec_state(spec_path)
    st.markdown(f"**Spec 状态**：`{spec.spec_status}`")
    if spec.executive_summary:
        st.markdown(spec.executive_summary)

    updated_sections: list[VisualReportSection] = []
    for section_index, section in enumerate(spec.sections):
        status_label = section.status
        expanded = section.status != "unsolved"
        with st.expander(f"{section.title} ({status_label})", expanded=expanded):
            if section.sub_question:
                st.caption(section.sub_question)
            if section.narrative:
                st.markdown(section.narrative)
            updated_charts: list[ChartBinding] = []
            for chart_index, chart in enumerate(section.charts):
                st.markdown(f"##### Chart: `{chart.chart_id}`")
                updated_charts.append(
                    render_chart_editor(
                        spec_path=spec_path,
                        section_index=section_index,
                        chart_index=chart_index,
                        chart=chart,
                    )
                )
            updated_sections.append(section.model_copy(update={"charts": updated_charts}))

    updated_spec = spec.model_copy(update={"sections": updated_sections})
    save_spec_state(spec_path, updated_spec)

    col1, col2 = st.columns(2)
    confirmed = False
    with col1:
        if st.button("保存 Spec 草稿", key=f"save_spec::{spec_path}"):
            save_visual_report_spec(updated_spec, spec_path)
            st.success("Spec 草稿已保存。")
    with col2:
        if st.button("确认 Spec", type="primary", key=f"confirm_spec::{spec_path}"):
            confirmed_spec = updated_spec.model_copy(update={"spec_status": "confirmed"})
            save_visual_report_spec(confirmed_spec, spec_path)
            save_spec_state(spec_path, confirmed_spec)
            st.success("Spec 已确认，可渲染 HTML 报告。")
            confirmed = True

    if spec.data_gaps:
        st.markdown("#### 数据缺口")
        for gap in spec.data_gaps:
            st.markdown(f"- {gap}")

    with st.expander("查看 Spec JSON"):
        st.code(json.dumps(updated_spec.model_dump(mode="json"), ensure_ascii=False, indent=2), language="json")

    return updated_spec, confirmed
