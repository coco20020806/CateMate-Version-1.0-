"""CateMate V1 dashboard: natural language pipeline + manifest review + PPT-ready."""

from __future__ import annotations

import json
import sys
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.category_confirmation_editor import render_category_confirmation_editor
from app.clarification_editor import (
    load_understanding_spec,
    mark_clarification_completed,
    render_answered_clarifications,
    render_clarification_editor,
)
from app.confirmation_editor import render_confirmation_editor
from catemate.core.paths import OUTPUTS_DIR, PROCESSED_DATA_DIR, PROJECT_ROOT as CATEMATE_ROOT
from catemate.pipeline.manifest import (
    PipelineManifest,
    iter_pipeline_manifest_paths,
    load_pipeline_manifest,
    resolve_manifest_path,
    update_and_save_manifest,
)
from app.pipeline_runtime import (
    run_conclusion_brief_subprocess,
    run_pipeline_continue_after_category_confirmation_subprocess,
    run_pipeline_continue_from_manifest_subprocess,
    run_pipeline_from_request_text_subprocess,
    run_ppt_ready_subprocess,
    run_visual_report_subprocess,
)
from app.visual_report_editor import render_visual_report_editor
from catemate.pipeline.runner import PipelineRunResult
from catemate.understanding.category_confirmation import is_category_confirmation_complete
from catemate.understanding.clarification import is_clarification_complete
from catemate.understanding.clarification_merge import needs_clarification_merge
from catemate.understanding.schemas import RequirementUnderstandingSpec

MANIFEST_GLOB = "pipeline_manifest_*.json"
MANIFEST_MANUAL_SELECT_KEY = "manifest_manually_selected"
DASHBOARD_MODE_KEY = "dashboard_mode"
PENDING_DASHBOARD_MODE_KEY = "_pending_dashboard_mode"
LAST_PIPELINE_MESSAGE_KEY = "last_pipeline_message"


def manifest_path_attr(manifest: PipelineManifest, name: str) -> str | None:
    """Read optional manifest path; safe when Streamlit cached an older PipelineManifest class."""
    return getattr(manifest, name, None)


STATUS_ACTION_HINTS: dict[str, str] = {
    "awaiting_category_confirmation": "待确认类目",
    "category_confirmed": "可继续 SolveLoop",
    "awaiting_clarification": "待澄清",
    "awaiting_rawdata_clarification": "待补数据",
    "clarification_completed": "可继续",
    "understanding_generated": "可继续",
    "workbook_generated": "待确认",
    "data_workbook_generated": "V2 数据已就绪",
    "planning_generated": "待确认",
    "module_selection_generated": "可继续",
    "ppt_ready_generated": "已完成",
    "blocked_by_understanding": "需修改需求重跑",
    "failed": "运行失败",
}


def active_workbook_session_key(manifest_path: str) -> str:
    return f"active_workbook::{manifest_path}"


def normalize_path_key(path: str | Path) -> str:
    return str(Path(path).resolve()).casefold()


def list_manifest_files() -> list[Path]:
    return iter_pipeline_manifest_paths(OUTPUTS_DIR)


def build_manifest_catalog() -> list[dict[str, object]]:
    catalog: list[dict[str, object]] = []
    seen_labels: dict[str, int] = {}

    for path in list_manifest_files():
        resolved = path.resolve()
        try:
            manifest = load_pipeline_manifest(resolved)
            case_id = manifest.case_id or resolved.stem
            timestamp = manifest.timestamp or "—"
            status = manifest.status or "—"
            request_preview = (manifest.request_text or "").strip().replace("\n", " ")
            if len(request_preview) > 48:
                request_preview = request_preview[:48] + "…"
            label = f"{case_id} | {timestamp} | {status}"
            hint = STATUS_ACTION_HINTS.get(status, "")
            if hint:
                label = f"{label} | {hint}"
            if request_preview:
                label = f"{label} | {request_preview}"
        except Exception:
            manifest = None
            case_id = resolved.stem
            timestamp = "—"
            status = "—"
            label = resolved.name

        if label in seen_labels:
            seen_labels[label] += 1
            label = f"{label} ({resolved.name})"
        else:
            seen_labels[label] = 1

        catalog.append(
            {
                "path": resolved,
                "label": label,
                "case_id": case_id,
                "timestamp": timestamp,
                "status": status,
                "mtime": resolved.stat().st_mtime,
                "manifest": manifest,
            }
        )
    return catalog


def find_catalog_label_for_path(catalog: list[dict[str, object]], manifest_path: Path) -> str | None:
    target = normalize_path_key(manifest_path)
    for entry in catalog:
        path = entry["path"]
        assert isinstance(path, Path)
        if normalize_path_key(path) == target:
            return str(entry["label"])
    return None


def align_manifest_pick_label(catalog: list[dict[str, object]], active_path: Path | None) -> None:
    if not catalog or active_path is None:
        return
    label = find_catalog_label_for_path(catalog, active_path)
    if label is not None:
        st.session_state["manifest_pick_label"] = label


def prepare_post_pipeline_navigation(
    result: PipelineRunResult,
    manifest_path: Path,
) -> None:
    """Pin manifest, stash flash message, and switch to history workflow view."""
    st.session_state["active_manifest_path"] = str(manifest_path.resolve())
    st.session_state[MANIFEST_MANUAL_SELECT_KEY] = True

    fresh_catalog = build_manifest_catalog()
    label = find_catalog_label_for_path(fresh_catalog, manifest_path)
    if label is not None:
        st.session_state["manifest_pick_label"] = label

    if result.exit_code == 0:
        if result.manifest and result.manifest.status == "awaiting_category_confirmation":
            message = (
                "warning",
                "Pipeline 已暂停：请先在「类目定位确认」中勾选类目并点击【确认类目】。",
            )
        elif result.manifest and result.manifest.status == "awaiting_clarification":
            message = (
                "warning",
                "Pipeline 已暂停：请在下方「需求澄清」中逐题回答或跳过后再继续。",
            )
        else:
            message = ("success", "Pipeline 运行完成。")
    else:
        message = (
            "error",
            f"Pipeline 运行失败（exit {result.exit_code}）：{result.error_message or '未知错误'}",
        )
    st.session_state[LAST_PIPELINE_MESSAGE_KEY] = message
    queue_dashboard_mode("history")


def apply_pending_dashboard_mode() -> None:
    """Apply a queued mode switch before the mode radio widget is created."""
    pending = st.session_state.pop(PENDING_DASHBOARD_MODE_KEY, None)
    if pending is not None:
        st.session_state[DASHBOARD_MODE_KEY] = pending


def queue_dashboard_mode(mode: str) -> None:
    """Queue a dashboard mode change for the next rerun (widget keys cannot be set mid-run)."""
    st.session_state[PENDING_DASHBOARD_MODE_KEY] = mode


def render_flash_message() -> None:
    message = st.session_state.pop(LAST_PIPELINE_MESSAGE_KEY, None)
    if not message:
        return
    level, text = message
    if level == "success":
        st.success(text)
    elif level == "warning":
        st.warning(text)
    else:
        st.error(text)


def render_mode_switcher() -> str:
    if DASHBOARD_MODE_KEY not in st.session_state:
        st.session_state[DASHBOARD_MODE_KEY] = "new"

    st.radio(
        "视图",
        options=["new", "history"],
        format_func=lambda value: "新建需求" if value == "new" else "历史需求",
        horizontal=True,
        key=DASHBOARD_MODE_KEY,
        label_visibility="collapsed",
    )
    return str(st.session_state[DASHBOARD_MODE_KEY])


def switch_to_history_manifest(manifest_path: Path, catalog: list[dict[str, object]]) -> None:
    st.session_state["active_manifest_path"] = str(manifest_path.resolve())
    st.session_state[MANIFEST_MANUAL_SELECT_KEY] = True
    label = find_catalog_label_for_path(catalog, manifest_path)
    if label is not None:
        st.session_state["manifest_pick_label"] = label
    queue_dashboard_mode("history")
    st.rerun()


def sync_active_manifest(catalog: list[dict[str, object]]) -> Path | None:
    if not catalog:
        return None

    latest_path = catalog[0]["path"]
    assert isinstance(latest_path, Path)

    if MANIFEST_MANUAL_SELECT_KEY not in st.session_state:
        st.session_state[MANIFEST_MANUAL_SELECT_KEY] = False

    if not st.session_state[MANIFEST_MANUAL_SELECT_KEY]:
        st.session_state["active_manifest_path"] = str(latest_path)
        return latest_path

    active_key = st.session_state.get("active_manifest_path")
    if active_key:
        active_norm = normalize_path_key(active_key)
        for entry in catalog:
            path = entry["path"]
            assert isinstance(path, Path)
            if normalize_path_key(path) == active_norm:
                return path

    st.session_state["active_manifest_path"] = str(latest_path)
    return latest_path


def display_path(path_string: str | None) -> str:
    if not path_string:
        return "—"
    path = resolve_manifest_path(CATEMATE_ROOT, path_string)
    if path is None:
        return path_string
    try:
        return str(path.relative_to(CATEMATE_ROOT))
    except ValueError:
        return str(path)


def load_json_path(path_string: str | None) -> dict | None:
    path = resolve_manifest_path(CATEMATE_ROOT, path_string)
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def render_status_badge(status: str) -> None:
    if status in {"workbook_generated", "ppt_ready_generated", "ready", "completed", "clarification_completed"}:
        st.success(status)
    elif status in {"failed", "blocked_by_understanding"}:
        st.error(status)
    elif status == "awaiting_clarification":
        st.warning(status)
    elif status == "awaiting_category_confirmation":
        st.warning(status)
    elif status.endswith("_generated"):
        st.info(status)
    else:
        st.warning(status or "—")


def clarification_gate_passed(manifest: PipelineManifest) -> bool:
    if manifest.planning_mode == "v2_solve_loop":
        if manifest.status == "data_workbook_generated":
            return True
        spec_path = resolve_manifest_path(CATEMATE_ROOT, manifest.understanding_spec_path)
        if spec_path is None or not spec_path.exists():
            return manifest.status not in {"awaiting_clarification", "awaiting_rawdata_clarification"}
        try:
            spec = load_understanding_spec(spec_path)
        except Exception:
            return False
        if not is_clarification_complete(spec):
            return False
        # 澄清题已在 UI 处理完（含跳过 rawdata）后，不再阻塞后续区块展示
        return True
    if manifest.planning_mode != "module_selection":
        return True
    if not manifest.understanding_spec_path:
        return True
    spec_path = resolve_manifest_path(CATEMATE_ROOT, manifest.understanding_spec_path)
    if spec_path is None or not spec_path.exists():
        return False
    try:
        spec = load_understanding_spec(spec_path)
    except Exception:
        return False
    if not spec.clarifying_questions:
        return True
    return is_clarification_complete(spec)


def render_manifest_summary(manifest: PipelineManifest, manifest_path: Path | None = None) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Case ID", manifest.case_id or "—")
    col2.metric("Planning 模式", manifest.planning_mode or "—")
    with col3:
        st.markdown("**Pipeline 状态**")
        render_status_badge(manifest.status)
    col4.metric("生成时间", manifest.timestamp or manifest.created_at or "—")

    if manifest.error_message:
        st.error(f"错误步骤：{manifest.error_step} — {manifest.error_message}")

    st.markdown("#### 产物路径")
    rows = [
        ("Pipeline manifest", display_path(str(manifest_path) if manifest_path else None)),
        ("Case config", display_path(manifest.case_config_path)),
        ("需求理解 spec", display_path(manifest.understanding_spec_path)),
        ("Module selection plan", display_path(manifest.module_selection_plan_path)),
        ("Report blueprint", display_path(manifest_path_attr(manifest, "report_blueprint_path"))),
        ("Analysis plan", display_path(manifest_path_attr(manifest, "analysis_plan_path"))),
        ("Solve loop state", display_path(manifest_path_attr(manifest, "solve_loop_state_path"))),
        ("Solve verdict", display_path(manifest_path_attr(manifest, "solve_verdict_path"))),
        ("Data workbook (V2)", display_path(manifest_path_attr(manifest, "data_workbook_path"))),
        ("Sub-L3 筛选 CSV 目录", display_path(manifest_path_attr(manifest, "subset_scope_dir"))),
        ("Sub-L3 筛选规则 (JSON)", display_path(manifest_path_attr(manifest, "sub_l3_filter_spec_path"))),
        ("Sub-L3 筛选规则 (Markdown)", display_path(manifest_path_attr(manifest, "sub_l3_filter_rules_path"))),
        ("Planning spec", display_path(manifest.planning_spec_path)),
        ("数据需求 workbook", display_path(manifest.requirement_workbook_path)),
        ("PPT-ready workbook", display_path(manifest.ppt_ready_workbook_path)),
        ("HTML preview", display_path(manifest.html_preview_path)),
        ("Visual Report Spec", display_path(manifest_path_attr(manifest, "visual_report_spec_path"))),
        ("HTML 报告", display_path(manifest_path_attr(manifest, "html_report_path"))),
        ("结论简报 (Markdown)", display_path(manifest_path_attr(manifest, "conclusion_brief_path"))),
        ("结论简报 (JSON)", display_path(manifest_path_attr(manifest, "conclusion_brief_json_path"))),
    ]
    for label, path_text in rows:
        st.markdown(f"- **{label}**：`{path_text}`")


def _v2_pipeline_needs_continue_after_category(manifest: PipelineManifest) -> bool:
    """True when category gate passed but SolveLoop / workbook was never produced."""
    if manifest.planning_mode != "v2_solve_loop":
        return False
    if manifest_path_attr(manifest, "data_workbook_path"):
        return False
    return manifest.status in {"category_confirmed", "failed"}


def render_category_confirmation_section(manifest: PipelineManifest, manifest_path: Path) -> bool:
    """Render category gate. Returns True when category confirmation is complete."""
    st.subheader("2. 类目定位确认")
    if manifest.planning_mode not in {"module_selection", "v2_solve_loop"}:
        st.info("当前 planning_mode 无需类目确认 gate。")
        return True

    spec_path = resolve_manifest_path(CATEMATE_ROOT, manifest.understanding_spec_path)
    if spec_path is None or not spec_path.exists():
        st.info("尚无 understanding spec。")
        return False

    def _on_confirmed(_spec: RequirementUnderstandingSpec) -> None:
        with st.spinner("类目已确认，正在继续 pipeline…"):
            result = run_pipeline_continue_after_category_confirmation_subprocess(manifest_path)
            if result.exit_code == 0:
                st.session_state[LAST_PIPELINE_MESSAGE_KEY] = ("success", "类目确认完成，pipeline 已继续。")
            else:
                st.session_state[LAST_PIPELINE_MESSAGE_KEY] = (
                    "error",
                    result.error_message or "继续 pipeline 失败。",
                )

    _, complete = render_category_confirmation_editor(
        spec_path,
        manifest,
        manifest_path,
        on_category_confirmed=_on_confirmed,
    )
    if complete and _v2_pipeline_needs_continue_after_category(manifest):
        st.warning(
            "类目已确认，但 SolveLoop / Data Workbook 尚未生成。"
            "若上次自动续跑失败，可点击下方按钮重试。"
        )
        if st.button(
            "继续生成 SolveLoop / Data Workbook",
            type="primary",
            key=f"continue_after_category::{normalize_path_key(manifest_path)}",
        ):
            with st.spinner("正在续跑 pipeline…"):
                result = run_pipeline_continue_after_category_confirmation_subprocess(manifest_path)
            if result.exit_code == 0:
                st.session_state[LAST_PIPELINE_MESSAGE_KEY] = ("success", "Pipeline 已继续。")
                st.rerun()
            else:
                st.error(result.error_message or "续跑失败。")
    return complete


def render_understanding_section(manifest: PipelineManifest) -> None:
    st.subheader("3. 需求理解")
    if not manifest.understanding_spec_path:
        st.info("当前运行未生成 understanding spec，可能是 ai_direct 模式。")
        return

    spec = load_json_path(manifest.understanding_spec_path)
    if spec is None:
        st.warning("无法读取 understanding spec 文件。")
        return

    understood = spec.get("understood") or {}
    col1, col2, col3 = st.columns(3)
    col1.metric("状态", spec.get("status", "—"))
    col2.write(f"**目标站点**：{', '.join(understood.get('target_sites') or []) or '—'}")
    col3.write(f"**交付格式**：{understood.get('delivery_format') or '—'}")

    st.markdown(f"**理解摘要**：{spec.get('conversation_summary') or '—'}")
    st.markdown(f"**目标类目文本**：{understood.get('target_category_text') or '—'}")
    st.markdown(f"**推断类目**：{understood.get('inferred_category') or '—'}")
    st.markdown(
        f"**分析意图**：{', '.join(understood.get('analysis_intents') or []) or '—'}"
    )

    candidates = understood.get("inferred_category_candidates") or []
    if candidates:
        st.markdown("**类目候选（L1/L2/L3）**")
        for item in candidates:
            st.markdown(
                f"- `{item.get('category_path', '')}` "
                f"（置信度：{item.get('confidence', '—')}）— {item.get('reason', '')}"
            )

    assumptions = spec.get("assumptions") or []
    if assumptions:
        with st.expander(f"假设（{len(assumptions)}）", expanded=False):
            for item in assumptions:
                content = item.get("content") if isinstance(item, dict) else str(item)
                st.markdown(f"- {content}")

    uncertainties = spec.get("uncertainties") or []
    if uncertainties:
        with st.expander(f"不确定项（{len(uncertainties)}）", expanded=False):
            for item in uncertainties:
                st.markdown(f"- **{item.get('topic', '')}**：{item.get('description', '')}")

    questions = spec.get("clarifying_questions") or []
    if questions:
        with st.expander(f"澄清问题（{len(questions)}）", expanded=False):
            for item in questions:
                block = "阻塞" if item.get("blocks_module_selection") else "非阻塞"
                st.markdown(f"- [{block}] {item.get('question', '')}")

    with st.expander("查看 understanding JSON 原文"):
        st.json(spec)


def _answers_newer_than_artifacts(manifest: PipelineManifest, spec: RequirementUnderstandingSpec) -> bool:
    """True when user answered clarifications after downstream files were written."""
    from datetime import datetime, timezone

    if not spec.user_answers:
        return False

    def _parse_iso(value: str) -> datetime | None:
        text = (value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    answer_times = [_parse_iso(item.answered_at) for item in spec.user_answers]
    answer_times = [item for item in answer_times if item is not None]
    if not answer_times:
        return bool(manifest.module_selection_plan_path or manifest.planning_spec_path or manifest.requirement_workbook_path)

    latest_answer = max(answer_times)
    artifact_paths = [
        resolve_manifest_path(CATEMATE_ROOT, manifest.module_selection_plan_path),
        resolve_manifest_path(CATEMATE_ROOT, manifest.planning_spec_path),
        resolve_manifest_path(CATEMATE_ROOT, manifest.requirement_workbook_path),
    ]
    for path in artifact_paths:
        if path is None or not path.exists():
            continue
        artifact_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if latest_answer > artifact_time:
            return True
    return False


def render_clarification_section(manifest: PipelineManifest, manifest_path: Path) -> bool:
    """Render clarification UI. Returns True when gate passed."""
    st.subheader("4. 需求澄清")
    if manifest.planning_mode == "v2_solve_loop":
        pass
    elif manifest.planning_mode != "module_selection":
        st.info("ai_direct 模式无理解澄清 gate。")
        return True

    spec_path = resolve_manifest_path(CATEMATE_ROOT, manifest.understanding_spec_path)
    if spec_path is None or not spec_path.exists():
        st.info("尚无 understanding spec。")
        return False

    try:
        spec = load_understanding_spec(spec_path)
    except Exception as exc:
        st.error(f"读取 understanding spec 失败：{exc}")
        return False

    render_answered_clarifications(spec)

    if not spec.clarifying_questions:
        st.info("本次理解未生成澄清问题，可直接继续。")
        return True

    complete = is_clarification_complete(spec)
    if not complete or manifest.status in {"awaiting_clarification", "awaiting_rawdata_clarification"}:
        _, complete = render_clarification_editor(
            spec_path,
            manifest,
            manifest_path,
            on_clarification_complete=lambda _updated: None,
        )

    if complete:
        if manifest.status in {"awaiting_clarification", "awaiting_rawdata_clarification"}:
            mark_clarification_completed(manifest, manifest_path)
            manifest = load_pipeline_manifest(manifest_path)

        downstream_stale = needs_clarification_merge(spec) and _answers_newer_than_artifacts(manifest, spec)

        if downstream_stale:
            st.warning(
                "澄清答案已记录，但当前 manifest 的下游产物可能仍是澄清/合并前生成的。"
                "请点击下方按钮重新生成（将调用 LLM 合并澄清答案并刷新后续步骤）。"
            )

        if manifest.planning_mode == "v2_solve_loop":
            show_continue = (
                manifest.status != "data_workbook_generated"
                and is_clarification_complete(spec)
                and (
                    manifest.status == "awaiting_rawdata_clarification"
                    or manifest.status == "category_confirmed"
                    or downstream_stale
                    or manifest.status in {"clarification_completed", "understanding_generated"}
                )
            )
        else:
            show_continue = manifest.status != "ppt_ready_generated" and (
                not manifest.module_selection_plan_path
                or downstream_stale
                or manifest.status in {"clarification_completed", "understanding_generated"}
            )

        if show_continue:
            label = (
                "重新生成 SolveLoop / Data Workbook（合并澄清答案）"
                if downstream_stale and manifest.planning_mode == "v2_solve_loop"
                else "重新生成 Module Selection / Workbook（合并澄清答案）"
                if downstream_stale
                else "继续生成 SolveLoop / Data Workbook"
                if manifest.planning_mode == "v2_solve_loop"
                else "继续生成 Module Selection / Workbook"
            )
            if st.button(label, type="primary", key="continue_after_clarification"):
                with st.spinner("正在合并澄清答案并续跑 pipeline..."):
                    if manifest.status == "category_confirmed":
                        result = run_pipeline_continue_after_category_confirmation_subprocess(manifest_path)
                    else:
                        result = run_pipeline_continue_from_manifest_subprocess(manifest_path)
                if result.exit_code == 0:
                    st.session_state["active_manifest_path"] = str(manifest_path)
                    st.success("后续步骤已生成。")
                    st.rerun()
                else:
                    st.error(result.error_message or "续跑失败。")

    return clarification_gate_passed(manifest)


def render_module_card(module: dict, *, badge: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{module.get('module_id', '')}** — {module.get('module_name', '')} `{badge}`")
        st.caption(module.get("reason", ""))
        intents = module.get("matched_intents") or []
        if intents:
            st.markdown(f"匹配意图：`{', '.join(intents)}`")
        tables = module.get("source_tables") or []
        if tables:
            st.markdown(f"数据表：`{', '.join(tables)}`")
        charts = module.get("selected_chart_intents") or []
        if charts:
            chart_lines = [
                f"{c.get('chart_intent')} ({c.get('chart_type')})" for c in charts if isinstance(c, dict)
            ]
            st.markdown(f"图表意图：{', '.join(chart_lines)}")


def render_solve_loop_section(manifest: PipelineManifest, manifest_path: Path) -> None:
    st.subheader("5. V2 求解循环")
    if manifest.planning_mode != "v2_solve_loop":
        st.info("非 v2_solve_loop 模式，跳过求解循环展示。")
        return

    blueprint = load_json_path(manifest_path_attr(manifest, "report_blueprint_path"))
    plan = load_json_path(manifest_path_attr(manifest, "analysis_plan_path"))
    verdict = load_json_path(manifest_path_attr(manifest, "solve_verdict_path"))
    loop_state = load_json_path(manifest_path_attr(manifest, "solve_loop_state_path"))

    if blueprint:
        st.markdown(f"**报告目标**：{blueprint.get('goal', '—')}")
        for section in blueprint.get("sections") or []:
            st.markdown(
                f"- `{section.get('section_id')}` {section.get('title')} — {section.get('sub_question')}"
            )

    if plan:
        st.markdown("**AnalysisPlan runs**")
        for run in plan.get("runs") or []:
            st.markdown(
                f"- `{run.get('run_id')}` {run.get('module_id')} / {run.get('metric_id')} "
                f"({run.get('status')}) — {run.get('scope_label', '')}"
            )

    if loop_state:
        st.caption(
            f"阶段：{loop_state.get('phase')} · 迭代：{loop_state.get('loop_iteration')} "
            f"· 数据题：{len(loop_state.get('rawdata_questions') or [])}"
        )
        precompute = (loop_state.get("metadata") or {}).get("subset_precompute") or {}
        if precompute.get("hit"):
            st.caption(
                f"Sub-L3 预筛：{precompute.get('entries', 0)} 个切片，"
                f"共 {precompute.get('output_rows', 0)} 行匹配 item 数据"
            )

    subset_scope_dir = manifest_path_attr(manifest, "subset_scope_dir")
    if subset_scope_dir:
        st.markdown(f"**Sub-L3 筛选 CSV 目录**：`{display_path(subset_scope_dir)}`")
        rules_md = manifest_path_attr(manifest, "sub_l3_filter_rules_path")
        if rules_md:
            rules_path = resolve_manifest_path(CATEMATE_ROOT, rules_md)
            if rules_path and rules_path.exists():
                with st.expander("查看 Sub-L3 筛选规则", expanded=False):
                    st.markdown(rules_path.read_text(encoding="utf-8"))

    if verdict:
        st.success(
            f"Verify：{verdict.get('verdict')} · exit={verdict.get('exit_reason') or '—'}"
        )

    data_workbook_path = manifest_path_attr(manifest, "data_workbook_path")
    if data_workbook_path:
        st.markdown(f"**Data Workbook**：`{display_path(data_workbook_path)}`")

    if manifest.status == "awaiting_rawdata_clarification" and loop_state:
        rawdata_questions = loop_state.get("rawdata_questions") or []
        missing_count = sum(
            1 for q in rawdata_questions if q.get("clarification_kind", "missing_rawdata") == "missing_rawdata"
        )
        plan_config_count = len(rawdata_questions) - missing_count
        detail = f"缺源数据 {missing_count} 条"
        if plan_config_count:
            detail += f"，计划配置问题 {plan_config_count} 条（无法通过上传文件解决）"
        st.warning(f"存在待处理数据澄清：{detail}。请在澄清区补充文件路径、处理计划问题或选择跳过。")
        if st.button("以 partial 继续（不再补数）", key="v2_decline_data"):
            from catemate.pipeline.v2_runner import continue_v2_solve_loop
            from app.clarification_editor import load_understanding_spec

            spec_path = resolve_manifest_path(CATEMATE_ROOT, manifest.understanding_spec_path)
            if spec_path and spec_path.exists():
                spec = load_understanding_spec(spec_path)
                result = continue_v2_solve_loop(
                    manifest_path=manifest_path,
                    manifest=manifest,
                    understanding_spec=spec,
                    understanding_spec_path=spec_path,
                    output_dir=manifest_path.parent,
                    safe_case_id=manifest.case_id,
                    stamp=manifest.timestamp,
                    processed_data_dir=PROCESSED_DATA_DIR,
                    user_declined_data=True,
                )
                if result.exit_code == 0:
                    st.rerun()
                else:
                    st.error(result.error_message or "续跑失败")


def render_module_selection_section(manifest: PipelineManifest) -> None:
    st.subheader("5. Module Selection")
    if not manifest.module_selection_plan_path:
        st.info("当前运行未生成 module selection plan。")
        return

    plan = load_json_path(manifest.module_selection_plan_path)
    if plan is None:
        st.warning("无法读取 module selection plan 文件。")
        return

    st.caption(plan.get("understanding_summary") or "")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Selected", len(plan.get("selected_modules") or []))
    col2.metric("Optional", len(plan.get("optional_modules") or []))
    col3.metric("Needs confirmation", len(plan.get("needs_confirmation_modules") or []))
    col4.metric("Rejected", len(plan.get("rejected_modules") or []))

    for module in plan.get("selected_modules") or []:
        render_module_card(module, badge="selected")
    for module in plan.get("optional_modules") or []:
        render_module_card(module, badge="optional")
    for module in plan.get("needs_confirmation_modules") or []:
        render_module_card(module, badge="needs_confirmation")

    rejected = plan.get("rejected_modules") or []
    if rejected:
        with st.expander(f"Rejected modules（{len(rejected)}）"):
            for module in rejected:
                render_module_card(module, badge="rejected")

    with st.expander("查看 module selection JSON 原文"):
        st.json(plan)


def render_confirmation_section(
    manifest: PipelineManifest,
    manifest_path: Path,
) -> tuple[bool, Path | None]:
    st.subheader("6. 确认与编辑")
    if not manifest.requirement_workbook_path:
        st.info("当前 manifest 尚无 requirement workbook。请先生成数据需求 workbook。")
        return False, None

    workbook_path = resolve_manifest_path(CATEMATE_ROOT, manifest.requirement_workbook_path)
    if workbook_path is None or not workbook_path.exists():
        st.warning("Requirement workbook 文件不存在。")
        return False, None

    session_key = active_workbook_session_key(str(manifest_path))
    override = st.session_state.get(session_key)
    if override:
        override_path = Path(override)
        if override_path.exists():
            workbook_path = override_path

    st.markdown(f"**当前 workbook**：`{display_path(str(workbook_path))}`")

    def on_workbook_saved(saved_path: Path) -> None:
        update_and_save_manifest(
            manifest_path=manifest_path,
            case_id=manifest.case_id,
            timestamp=manifest.timestamp,
            request_text=manifest.request_text,
            provider=manifest.provider,
            model=manifest.model,
            planning_mode=manifest.planning_mode,
            case_config_path=resolve_manifest_path(CATEMATE_ROOT, manifest.case_config_path),
            understanding_spec_path=resolve_manifest_path(CATEMATE_ROOT, manifest.understanding_spec_path),
            module_selection_plan_path=resolve_manifest_path(
                CATEMATE_ROOT, manifest.module_selection_plan_path
            ),
            planning_spec_path=resolve_manifest_path(CATEMATE_ROOT, manifest.planning_spec_path),
            requirement_workbook_path=saved_path,
            ppt_ready_workbook_path=resolve_manifest_path(CATEMATE_ROOT, manifest.ppt_ready_workbook_path),
            html_preview_path=resolve_manifest_path(CATEMATE_ROOT, manifest.html_preview_path),
            status=manifest.status,
        )
        st.session_state[session_key] = str(saved_path.resolve())

    active_workbook, gate_ok = render_confirmation_editor(
        workbook_path,
        on_workbook_saved=on_workbook_saved,
    )
    st.session_state[session_key] = str(active_workbook.resolve())
    return gate_ok, active_workbook


def render_ppt_ready_section(
    manifest: PipelineManifest,
    manifest_path: Path | None,
    gate_ok: bool,
    workbook_path: Path | None,
) -> None:
    st.subheader("7. 生成 PPT-ready workbook + HTML preview")

    if manifest.ppt_ready_workbook_path:
        st.markdown(f"- **已有 PPT-ready**：`{display_path(manifest.ppt_ready_workbook_path)}`")
    if manifest.html_preview_path:
        st.markdown(f"- **已有 HTML preview**：`{display_path(manifest.html_preview_path)}`")

    if not gate_ok:
        st.warning("确认门禁未通过，或尚未保存确认结果。请先完成确认并点击「保存确认结果」。")
        return

    planning_path = resolve_manifest_path(CATEMATE_ROOT, manifest.planning_spec_path)
    if workbook_path is None or planning_path is None:
        st.warning("缺少 planning spec 或 requirement workbook 路径。")
        return

    if st.button("生成 PPT-ready workbook 和 HTML preview", type="primary"):
        with st.spinner("正在生成 PPT-ready workbook 与 HTML preview..."):
            result = run_ppt_ready_subprocess(
                requirement_workbook=workbook_path,
                planning_spec_path=planning_path,
                pipeline_manifest_path=manifest_path,
                processed_manifest_path=PROCESSED_DATA_DIR / "processed_manifest.yaml",
                processed_data_dir=PROCESSED_DATA_DIR,
            )
        if result.exit_code != 0:
            message = result.error_message
            if "Confirmation gate blocked" in message or "blocking_items" in message:
                st.error(message)
            else:
                st.error(f"生成失败：{message}")
            return

        st.session_state["active_manifest_path"] = (
            str(manifest_path) if manifest_path is not None else st.session_state.get("active_manifest_path")
        )
        st.success(result.gate_message or "PPT-ready 生成完成。")
        st.markdown(f"- **PPT-ready workbook**：`{result.output_path}`")
        if result.html_preview_path:
            st.markdown(f"- **HTML preview**：`{result.html_preview_path}`")
        st.markdown(f"- 图表 sheet 数：{result.sheet_count}；警告数：{result.warning_count}")
        st.rerun()


def render_new_requirement_section(manifest_catalog: list[dict[str, object]]) -> None:
    st.header("新建需求")
    request_text = st.text_area(
        "自然语言需求",
        height=160,
        placeholder="请输入类目分析需求，例如站点、类目、趋势、价格、Top Listing、关键词等。",
    )
    planning_mode = st.selectbox(
        "Planning 模式",
        options=["v2_solve_loop", "module_selection", "ai_direct"],
        index=0,
        help="默认推荐 v2_solve_loop（求解循环 → Data Workbook）。module_selection 为 V1 链路。",
    )

    if st.button("生成数据需求 workbook", type="primary", disabled=not request_text.strip()):
        with st.spinner("正在运行 pipeline，请稍候（可能需要几分钟）..."):
            result = run_pipeline_from_request_text_subprocess(
                request_text=request_text.strip(),
                planning_mode=planning_mode,
            )
        if result.manifest_path is not None:
            prepare_post_pipeline_navigation(result, Path(result.manifest_path))
            st.rerun()
        elif result.exit_code == 0:
            st.success("Pipeline 运行完成。")
        else:
            st.error(f"Pipeline 运行失败（exit {result.exit_code}）：{result.error_message or '未知错误'}")

    if manifest_catalog:
        with st.expander(f"最近需求（{min(len(manifest_catalog), 3)} 条）", expanded=False):
            st.caption("快速回到未完成或最近处理的需求，不会离开「新建需求」默认首页。")
            for entry in manifest_catalog[:3]:
                path = entry["path"]
                assert isinstance(path, Path)
                status = str(entry.get("status") or "—")
                hint = STATUS_ACTION_HINTS.get(status, "")
                preview = str(entry.get("label") or path.name)
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{entry.get('case_id', path.stem)}** · `{status}`")
                    if hint:
                        st.caption(hint)
                    st.caption(preview)
                with col2:
                    if st.button("继续处理", key=f"continue_recent::{normalize_path_key(path)}"):
                        switch_to_history_manifest(path, manifest_catalog)


def render_history_manifest_picker(catalog: list[dict[str, object]]) -> Path | None:
    st.header("历史需求")
    st.caption(f"扫描目录：`{OUTPUTS_DIR}`（含 `runs/` 子目录），共 {len(catalog)} 条 pipeline manifest。")

    if not catalog:
        st.info("暂无历史需求。请先在「新建需求」中生成一次，或用 CLI 跑完一键链路后再来查看。")
        if st.button("去新建需求", type="primary"):
            queue_dashboard_mode("new")
            st.rerun()
        return None

    active_path = sync_active_manifest(catalog)
    latest_entry = catalog[0]
    latest_catalog_path = latest_entry["path"]
    assert isinstance(latest_catalog_path, Path)

    if active_path is not None:
        align_manifest_pick_label(catalog, active_path)

    if (
        active_path is not None
        and normalize_path_key(active_path) != normalize_path_key(latest_catalog_path)
        and st.session_state.get(MANIFEST_MANUAL_SELECT_KEY, False)
    ):
        st.warning(
            f"当前查看的不是最新运行。最新为 **{latest_entry['case_id']}** "
            f"（{latest_entry['timestamp']}，状态：{latest_entry['status']}）。"
        )

    tool_col1, tool_col2 = st.columns([1, 1])
    with tool_col1:
        if st.button("刷新并选中最新", help="重新扫描 outputs/，并切换到最新一次 pipeline 运行"):
            st.session_state[MANIFEST_MANUAL_SELECT_KEY] = False
            st.rerun()
    with tool_col2:
        st.caption("若在终端用 CLI 跑过新需求，请先点这里。")

    label_to_path = {str(entry["label"]): entry["path"] for entry in catalog}
    labels = list(label_to_path.keys())
    active_norm = normalize_path_key(active_path) if active_path else ""
    default_index = 0
    for index, entry in enumerate(catalog):
        path = entry["path"]
        assert isinstance(path, Path)
        if normalize_path_key(path) == active_norm:
            default_index = index
            break

    def on_manifest_pick_change() -> None:
        picked_label = st.session_state.get("manifest_pick_label")
        picked_path = label_to_path.get(picked_label)
        if picked_path is not None:
            st.session_state["active_manifest_path"] = str(picked_path)
            latest_norm = normalize_path_key(latest_catalog_path)
            picked_norm = normalize_path_key(picked_path)
            st.session_state[MANIFEST_MANUAL_SELECT_KEY] = picked_norm != latest_norm

    if not st.session_state.get(MANIFEST_MANUAL_SELECT_KEY, False):
        st.session_state["manifest_pick_label"] = labels[default_index]
    elif st.session_state.get("manifest_pick_label") not in labels:
        st.session_state["manifest_pick_label"] = labels[default_index]
    elif "manifest_pick_label" not in st.session_state:
        st.session_state["manifest_pick_label"] = labels[default_index]

    st.selectbox(
        "选择 pipeline manifest",
        options=labels,
        key="manifest_pick_label",
        on_change=on_manifest_pick_change,
        help="按时间倒序排列；最新一次在最上方。标签中含状态引导（待澄清 / 待确认等）。",
    )
    selected_label = st.session_state["manifest_pick_label"]
    selected_manifest_path = label_to_path[selected_label]
    assert isinstance(selected_manifest_path, Path)
    st.session_state["active_manifest_path"] = str(selected_manifest_path)
    return selected_manifest_path


def open_html_report_in_browser(html_path: Path) -> bool:
    """Open a local HTML report in the user's default browser."""
    return webbrowser.open(html_path.resolve().as_uri(), new=2)


def render_data_workbook_consume_section(manifest: PipelineManifest, manifest_path: Path) -> None:
    st.subheader("6. Data Workbook 消费（HTML 报告 / 结论简报）")
    data_workbook_path = manifest_path_attr(manifest, "data_workbook_path")
    if not data_workbook_path:
        st.info("尚无 Data Workbook。")
        return
    wb_path = resolve_manifest_path(CATEMATE_ROOT, data_workbook_path)
    if wb_path is None or not wb_path.exists():
        st.warning("Data Workbook 文件不存在。")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("从 Data Workbook 生成 HTML 预览", key="build_html_from_data_wb"):
            from catemate.ppt_ready.build_from_data_workbook import build_html_from_data_workbook

            out = build_html_from_data_workbook(wb_path)
            update_and_save_manifest(
                manifest_path=manifest_path,
                case_id=manifest.case_id,
                timestamp=manifest.timestamp,
                request_text=manifest.request_text,
                provider=manifest.provider,
                model=manifest.model,
                planning_mode=manifest.planning_mode,
                html_preview_path=out,
                status=manifest.status,
            )
            st.success(f"HTML 预览已生成：`{out}`")
            st.rerun()
    with col2:
        if st.button("生成 Visual Report Spec", type="primary", key="build_visual_report_spec"):
            with st.spinner("正在生成 Visual Report Spec（规则 + LLM）..."):
                result = run_visual_report_subprocess(
                    pipeline_manifest_path=manifest_path,
                    mode="propose",
                )
            if result.exit_code != 0:
                st.error(result.error_message or "Visual Report Spec 生成失败。")
            else:
                st.session_state[LAST_PIPELINE_MESSAGE_KEY] = (
                    "success",
                    "Visual Report Spec 已生成，请在校对区确认。",
                )
                st.rerun()
    with col3:
        if st.button("生成结论简报", key="build_conclusion_brief"):
            with st.spinner("正在生成结论简报（LLM）..."):
                result = run_conclusion_brief_subprocess(pipeline_manifest_path=manifest_path)
            if result.exit_code != 0:
                st.error(result.error_message or "结论简报生成失败。")
            else:
                st.session_state[LAST_PIPELINE_MESSAGE_KEY] = (
                    "success",
                    "结论简报已生成。",
                )
                st.rerun()

    spec_path = resolve_manifest_path(
        CATEMATE_ROOT, manifest_path_attr(manifest, "visual_report_spec_path")
    )
    if spec_path and spec_path.exists():
        st.markdown(f"- **Visual Report Spec**：`{display_path(str(spec_path))}`")
        st.markdown("#### Gate C · Visual Report Spec 校对")
        _, confirmed = render_visual_report_editor(spec_path)
        if confirmed:
            st.rerun()

        from catemate.html_report.proposal_generator import load_visual_report_spec

        spec = load_visual_report_spec(spec_path)
        if spec.spec_status == "confirmed":
            if st.button("渲染 HTML 报告", type="primary", key="render_html_report"):
                with st.spinner("正在渲染 HTML 报告..."):
                    result = run_visual_report_subprocess(
                        pipeline_manifest_path=manifest_path,
                        mode="render",
                    )
                if result.exit_code != 0:
                    st.error(result.error_message or "HTML 报告渲染失败。")
                else:
                    st.session_state[LAST_PIPELINE_MESSAGE_KEY] = (
                        "success",
                        "HTML 报告已生成。",
                    )
                    st.rerun()
        else:
            st.info("请先确认 Visual Report Spec，再渲染 HTML 报告。")

    html_report_path = resolve_manifest_path(CATEMATE_ROOT, manifest_path_attr(manifest, "html_report_path"))
    if html_report_path and html_report_path.exists():
        col_path, col_open = st.columns([4, 1])
        with col_path:
            st.markdown(f"- **HTML 报告**：`{display_path(str(html_report_path))}`")
        with col_open:
            if st.button("在浏览器中打开", key="open_html_report_in_browser"):
                if open_html_report_in_browser(html_report_path):
                    st.success("已在浏览器中打开 HTML 报告。")
                else:
                    st.warning("无法自动打开浏览器，请手动打开上方文件路径。")

    brief_md_path = resolve_manifest_path(CATEMATE_ROOT, manifest_path_attr(manifest, "conclusion_brief_path"))
    brief_json_path = resolve_manifest_path(
        CATEMATE_ROOT, manifest_path_attr(manifest, "conclusion_brief_json_path")
    )
    if brief_md_path and brief_md_path.exists():
        st.markdown(f"- **结论简报 (Markdown)**：`{display_path(str(brief_md_path))}`")
        if brief_json_path and brief_json_path.exists():
            st.markdown(f"- **结论简报 (JSON)**：`{display_path(str(brief_json_path))}`")
        with st.expander("查看结论简报", expanded=False):
            st.markdown(brief_md_path.read_text(encoding="utf-8"))


def render_workflow_sections(manifest: PipelineManifest, selected_manifest_path: Path) -> None:
    render_manifest_summary(manifest, selected_manifest_path)

    st.divider()
    category_ok = render_category_confirmation_section(manifest, selected_manifest_path)
    if not category_ok:
        st.info("请先完成类目定位确认（勾选类目并点击【确认类目】），再进行后续步骤。")
        return

    try:
        manifest = load_pipeline_manifest(selected_manifest_path)
    except Exception:
        pass

    st.divider()
    render_understanding_section(manifest)

    st.divider()
    clarify_ok = render_clarification_section(manifest, selected_manifest_path)
    if not clarify_ok:
        st.info("请先完成需求澄清，再进行后续步骤。")
        return

    try:
        manifest = load_pipeline_manifest(selected_manifest_path)
    except Exception:
        pass

    st.divider()
    if manifest.planning_mode == "v2_solve_loop":
        render_solve_loop_section(manifest, selected_manifest_path)
        st.divider()
        if manifest_path_attr(manifest, "data_workbook_path"):
            render_data_workbook_consume_section(manifest, selected_manifest_path)
        return

    render_module_selection_section(manifest)

    st.divider()
    gate_ok, active_workbook = render_confirmation_section(manifest, selected_manifest_path)

    st.divider()
    render_ppt_ready_section(
        manifest,
        selected_manifest_path,
        gate_ok,
        active_workbook,
    )


def main() -> None:
    st.set_page_config(page_title="CateMate V1 总控台", layout="wide")
    st.title("CateMate V1 总控台")
    st.caption("从自然语言需求 → 理解 → 选模块 → 规划 → 确认 → PPT-ready 的一站式入口。")

    manifest_catalog = build_manifest_catalog()

    if DASHBOARD_MODE_KEY not in st.session_state:
        st.session_state[DASHBOARD_MODE_KEY] = "new"
    if MANIFEST_MANUAL_SELECT_KEY not in st.session_state:
        st.session_state[MANIFEST_MANUAL_SELECT_KEY] = False

    apply_pending_dashboard_mode()
    dashboard_mode = render_mode_switcher()
    st.divider()

    if dashboard_mode == "new":
        render_new_requirement_section(manifest_catalog)
        return

    render_flash_message()
    selected_manifest_path = render_history_manifest_picker(manifest_catalog)
    if selected_manifest_path is None:
        return

    try:
        manifest = load_pipeline_manifest(selected_manifest_path)
    except Exception as exc:
        st.error(f"读取 manifest 失败：{exc}")
        return

    render_workflow_sections(manifest, selected_manifest_path)


if __name__ == "__main__":
    main()
