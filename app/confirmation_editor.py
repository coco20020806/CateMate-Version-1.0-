"""Shared Streamlit UI for editing requirement workbook confirmation items."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd
import streamlit as st

from catemate.core.confirmation_gate import (
    STATUS_BLOCKED,
    STATUS_CONFIRMED,
    STATUS_NOT_NEEDED,
    STATUS_PENDING_CONFIRMATION,
    STATUS_PENDING_SUPPLEMENT,
    STATUS_SUPPLEMENTED,
    ConfirmationItem,
    GateResult,
    evaluate_confirmation_gate,
)
from catemate.core.confirmation_reader import (
    HEADER_BLOCK,
    HEADER_NAME,
    HEADER_REASON,
    HEADER_STATUS,
    HEADER_SUGGESTED_VALUE,
    read_confirmation_records,
)
from catemate.core.confirmation_writer import save_confirmation_updates

STATUS_OPTIONS = [
    STATUS_PENDING_CONFIRMATION,
    STATUS_PENDING_SUPPLEMENT,
    STATUS_SUPPLEMENTED,
    STATUS_CONFIRMED,
    STATUS_NOT_NEEDED,
    STATUS_BLOCKED,
]
ALLOWED_FINAL = {STATUS_CONFIRMED, STATUS_NOT_NEEDED}


def parse_block_flag(value: object) -> bool | None:
    text = str(value).strip().lower() if value is not None else ""
    if text in {"是", "yes", "true", "1", "y"}:
        return True
    if text in {"否", "no", "false", "0", "n"}:
        return False
    return None


def status_store_key(workbook: Path) -> str:
    return f"confirmation_statuses::{workbook.resolve()}"


def more_store_key(workbook: Path, row_number: int) -> str:
    return f"confirmation_more::{workbook.resolve()}::{row_number}"


def initialize_statuses(workbook: Path, records: list[dict[str, object]]) -> str:
    key = status_store_key(workbook)
    row_statuses = {int(record["row"]): str(record[HEADER_STATUS]) for record in records}
    if key not in st.session_state:
        st.session_state[key] = row_statuses
    else:
        for row_number, status in row_statuses.items():
            st.session_state[key].setdefault(row_number, status)
    return key


def build_items(records: list[dict[str, object]], statuses: dict[int, str]) -> list[ConfirmationItem]:
    return [
        ConfirmationItem(
            name=str(record[HEADER_NAME]),
            suggested_value=str(record[HEADER_SUGGESTED_VALUE]),
            status=statuses.get(int(record["row"]), str(record[HEADER_STATUS])),
            reason=str(record[HEADER_REASON]),
            blocks_ppt_ready=parse_block_flag(record.get(HEADER_BLOCK)),
        )
        for record in records
    ]


def count_nonblocking_reminders(items: list[ConfirmationItem]) -> int:
    return sum(
        1 for item in items if item.blocks_ppt_ready is False and item.status not in ALLOWED_FINAL
    )


def render_status_badge(status: str) -> None:
    if status == STATUS_CONFIRMED:
        st.success(status)
    elif status == STATUS_NOT_NEEDED:
        st.info(status)
    elif status == STATUS_BLOCKED:
        st.error(status)
    else:
        st.warning(status)


def render_gate_summary(items: list[ConfirmationItem], *, title: str = "确认门禁摘要") -> GateResult | None:
    st.markdown(f"#### {title}")
    try:
        gate_result = evaluate_confirmation_gate(items)
    except Exception as exc:
        st.error(f"计算 confirmation gate 失败：{exc}")
        return None

    pending_count = sum(1 for item in items if item.status not in ALLOWED_FINAL)
    confirmed_count = sum(1 for item in items if item.status == STATUS_CONFIRMED)
    not_needed_count = sum(1 for item in items if item.status == STATUS_NOT_NEEDED)
    reminder_count = count_nonblocking_reminders(items)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("确认项总数", len(items))
    m2.metric("已确认", confirmed_count)
    m3.metric("不需要", not_needed_count)
    m4.metric("待处理", pending_count)

    m5, m6, m7 = st.columns(3)
    m5.metric("阻塞项", len(gate_result.blocking_items))
    m6.metric("非阻塞提醒", reminder_count)
    m7.metric("可生成 PPT-ready", "是" if gate_result.can_generate else "否")

    if gate_result.can_generate:
        st.success(gate_result.message)
    else:
        st.warning(gate_result.message)
    return gate_result


def render_confirmation_row(workbook: Path, record: dict[str, object], statuses_key: str) -> None:
    row_number = int(record["row"])
    current_status = st.session_state[statuses_key].get(row_number, str(record[HEADER_STATUS]))

    with st.container(border=True):
        info_col, status_col, confirm_col, reject_col, more_col = st.columns([7, 1.4, 0.7, 0.7, 0.7])

        with info_col:
            st.markdown(f"**{record[HEADER_NAME]}**")
            suggested_value = str(record[HEADER_SUGGESTED_VALUE])
            reason = str(record[HEADER_REASON])
            question_text = reason.strip()
            if question_text and question_text != str(record[HEADER_NAME]).strip():
                st.write(question_text)
            if suggested_value:
                st.caption(f"建议值：{suggested_value}")
            elif reason and not question_text:
                st.caption(f"原因：{reason}")

        with status_col:
            render_status_badge(current_status)

        with confirm_col:
            if st.button("✓", key=f"confirm::{workbook}::{row_number}", help="确认"):
                st.session_state[statuses_key][row_number] = STATUS_CONFIRMED
                st.rerun()

        with reject_col:
            if st.button("×", key=f"reject::{workbook}::{row_number}", help="舍弃 / 不需要"):
                st.session_state[statuses_key][row_number] = STATUS_NOT_NEEDED
                st.rerun()

        with more_col:
            more_key = more_store_key(workbook, row_number)
            if st.button("...", key=f"more_button::{workbook}::{row_number}", help="更多状态"):
                st.session_state[more_key] = not st.session_state.get(more_key, False)
                st.rerun()

        if st.session_state.get(more_store_key(workbook, row_number), False):
            selected_status = st.selectbox(
                "选择其他状态",
                options=STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0,
                key=f"more_select::{workbook}::{row_number}",
            )
            if selected_status != current_status:
                st.session_state[statuses_key][row_number] = selected_status


def group_records(records: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        grouped[str(record[HEADER_NAME])].append(record)
    return dict(grouped)


def summarize_group_status(records: list[dict[str, object]], statuses: dict[int, str]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        counts[statuses.get(int(record["row"]), str(record[HEADER_STATUS]))] += 1
    return " / ".join(f"{status} {count}" for status, count in counts.items())


def render_group_actions(
    workbook: Path,
    records: list[dict[str, object]],
    statuses_key: str,
    group_name: str,
) -> None:
    action_col_1, action_col_2, _ = st.columns([1, 1, 5])
    with action_col_1:
        if st.button("全部 ✓", key=f"group_confirm::{workbook}::{group_name}", help="全部确认"):
            for record in records:
                st.session_state[statuses_key][int(record["row"])] = STATUS_CONFIRMED
            st.rerun()
    with action_col_2:
        if st.button("全部 ×", key=f"group_reject::{workbook}::{group_name}", help="全部舍弃 / 不需要"):
            for record in records:
                st.session_state[statuses_key][int(record["row"])] = STATUS_NOT_NEEDED
            st.rerun()


def render_confirmation_group(
    workbook: Path,
    group_name: str,
    records: list[dict[str, object]],
    statuses_key: str,
) -> None:
    statuses = st.session_state[statuses_key]
    status_summary = summarize_group_status(records, statuses)

    if len(records) == 1:
        render_confirmation_row(workbook, records[0], statuses_key)
        return

    with st.expander(f"{group_name}（{len(records)} 项｜{status_summary}）", expanded=False):
        st.caption("展开后选择需要保留的候选；✓ 表示确认，× 表示不需要。")
        render_group_actions(workbook, records, statuses_key, group_name)
        for record in records:
            render_confirmation_row(workbook, record, statuses_key)


def save_statuses(source: Path, statuses: dict[int, str], save_as_new: bool) -> Path:
    if save_as_new:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = source.parent / f"{source.stem}_confirmed_{timestamp}.xlsx"
    else:
        output_path = source
    return save_confirmation_updates(source, statuses, output_path)


def render_confirmation_editor(
    workbook: Path,
    *,
    on_workbook_saved: Callable[[Path], None] | None = None,
) -> tuple[Path, bool]:
    """Render editable confirmation UI. Returns (active_workbook_path, saved_gate_ok)."""
    try:
        records = read_confirmation_records(workbook)
    except Exception as exc:
        st.error(f"读取确认记录失败：{exc}")
        return workbook, False

    if not records:
        st.warning("该 workbook 的「确认记录」表没有可编辑的确认项。")
        return workbook, False

    active_workbook = workbook
    statuses_key = initialize_statuses(active_workbook, records)
    session_items = build_items(records, st.session_state[statuses_key])
    render_gate_summary(session_items, title="当前编辑状态（未保存也会反映在此）")

    saved_items = build_items(records, {int(r["row"]): str(r[HEADER_STATUS]) for r in records})
    saved_gate = evaluate_confirmation_gate(saved_items)
    if not saved_gate.can_generate:
        st.caption("已保存到文件的状态尚未通过门禁；请编辑后点击「保存确认结果」。")

    st.markdown("#### 确认项列表")
    st.caption("同类确认项会合并展示。✓ 已确认；× 不需要；... 可切换其他状态。")
    for group_name, group_items in group_records(records).items():
        render_confirmation_group(active_workbook, group_name, group_items, statuses_key)

    st.markdown("#### 保存确认结果")
    save_as_new = st.toggle("另存为新 workbook（推荐）", value=True, key=f"save_as_new::{active_workbook}")
    save_col, check_col = st.columns([1, 1])

    with save_col:
        if st.button("保存确认结果", type="primary", key=f"save_confirm::{active_workbook}"):
            try:
                saved_path = save_statuses(active_workbook, st.session_state[statuses_key], save_as_new)
            except (ValueError, OSError) as exc:
                st.error(f"保存失败：{exc}")
            else:
                active_workbook = saved_path
                st.success(f"已保存：{saved_path.name}")
                st.caption(str(saved_path))
                if on_workbook_saved is not None:
                    on_workbook_saved(saved_path)
                st.session_state.pop(status_store_key(workbook), None)
                st.rerun()

    with check_col:
        if st.button("检查已保存状态", key=f"check_gate::{active_workbook}"):
            try:
                fresh_records = read_confirmation_records(active_workbook)
                gate_result = evaluate_confirmation_gate(
                    build_items(fresh_records, {int(r["row"]): str(r[HEADER_STATUS]) for r in fresh_records})
                )
            except Exception as exc:
                st.error(f"检查失败：{exc}")
            else:
                if gate_result.can_generate:
                    st.success("已保存的 workbook 可以通过门禁，可生成 PPT-ready。")
                else:
                    st.warning(f"暂时不能进入下一步：仍有 {len(gate_result.blocking_items)} 个阻塞项。")
                    blocking_df = pd.DataFrame(
                        [
                            {
                                "确认项": item.name,
                                "当前状态": item.status,
                                "建议值": item.suggested_value,
                                "原因": item.reason,
                            }
                            for item in gate_result.blocking_items
                        ]
                    )
                    st.dataframe(blocking_df, hide_index=True, use_container_width=True)

    try:
        final_records = read_confirmation_records(active_workbook)
        final_gate = evaluate_confirmation_gate(
            build_items(final_records, {int(r["row"]): str(r[HEADER_STATUS]) for r in final_records})
        )
    except Exception:
        return active_workbook, False
    return active_workbook, final_gate.can_generate
