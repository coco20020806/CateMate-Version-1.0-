"""Pipeline manifest helpers for natural-language requirement runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from catemate.core.paths import ARCHIVE_DIR_NAMES
from catemate.scope.scope_cache import MANIFEST_FILENAME
from catemate.scope.sub_l3_artifacts import FILTER_RULES_MD_FILENAME, FILTER_SPEC_FILENAME


PIPELINE_VERSION = "v2"
MANIFEST_GLOB = "pipeline_manifest_*.json"


@dataclass
class PipelineManifest:
    """Lightweight record linking one pipeline run's artifacts."""

    case_id: str = ""
    timestamp: str = ""
    request_text: str = ""
    provider: str = ""
    model: str = ""
    planning_mode: str = "ai_direct"
    case_config_path: str | None = None
    understanding_spec_path: str | None = None
    module_selection_plan_path: str | None = None
    planning_spec_path: str | None = None
    requirement_workbook_path: str | None = None
    ppt_ready_workbook_path: str | None = None
    html_preview_path: str | None = None
    report_blueprint_path: str | None = None
    analysis_plan_path: str | None = None
    solve_loop_state_path: str | None = None
    solve_verdict_path: str | None = None
    data_workbook_path: str | None = None
    conclusion_brief_path: str | None = None
    conclusion_brief_json_path: str | None = None
    visual_report_spec_path: str | None = None
    html_report_path: str | None = None
    subset_scope_dir: str | None = None
    sub_l3_filter_spec_path: str | None = None
    sub_l3_filter_rules_path: str | None = None
    created_at: str = ""
    pipeline_version: str = PIPELINE_VERSION
    status: str = "in_progress"
    error_step: str | None = None
    error_message: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        # Never persist secrets; keep payload explicit and reviewable.
        payload.pop("extra", None)
        if self.extra:
            # Allow optional non-secret metadata only.
            for key, value in self.extra.items():
                if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
                    continue
                payload[key] = value
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineManifest":
        known = {
            "case_id",
            "timestamp",
            "request_text",
            "provider",
            "model",
            "planning_mode",
            "case_config_path",
            "understanding_spec_path",
            "module_selection_plan_path",
            "planning_spec_path",
            "requirement_workbook_path",
            "ppt_ready_workbook_path",
            "html_preview_path",
            "report_blueprint_path",
            "analysis_plan_path",
            "solve_loop_state_path",
            "solve_verdict_path",
            "data_workbook_path",
            "conclusion_brief_path",
            "conclusion_brief_json_path",
            "visual_report_spec_path",
            "html_report_path",
            "subset_scope_dir",
            "sub_l3_filter_spec_path",
            "sub_l3_filter_rules_path",
            "created_at",
            "pipeline_version",
            "status",
            "error_step",
            "error_message",
        }
        kwargs = {key: data.get(key) for key in known}
        extra = {key: value for key, value in data.items() if key not in known}
        manifest = cls(extra=extra, **kwargs)
        if manifest.subset_scope_dir is None and extra.get("subset_scope_dir"):
            manifest.subset_scope_dir = str(extra["subset_scope_dir"])
        if manifest.sub_l3_filter_spec_path is None and extra.get("sub_l3_filter_spec_path"):
            manifest.sub_l3_filter_spec_path = str(extra["sub_l3_filter_spec_path"])
        if manifest.sub_l3_filter_rules_path is None and extra.get("sub_l3_filter_rules_path"):
            manifest.sub_l3_filter_rules_path = str(extra["sub_l3_filter_rules_path"])
        return manifest


def default_manifest_path(output_dir: Path, case_id: str, timestamp: str) -> Path:
    safe = case_id.strip() or "unknown_case"
    return output_dir / f"pipeline_manifest_{safe}_{timestamp}.json"


def save_pipeline_manifest(manifest: PipelineManifest, path: Path) -> Path:
    """Write manifest JSON. Never includes API keys."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_pipeline_manifest(path: Path) -> PipelineManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid pipeline manifest (expected object): {path}")
    return PipelineManifest.from_dict(payload)


def find_latest_pipeline_manifest(outputs_dir: Path) -> Path | None:
    """Return newest pipeline_manifest_*.json by mtime, or None."""
    manifests = iter_pipeline_manifest_paths(outputs_dir)
    if not manifests:
        return None
    return manifests[0]


def iter_pipeline_manifest_paths(outputs_dir: Path) -> list[Path]:
    """List pipeline manifests under outputs (including outputs/runs), newest first."""
    if not outputs_dir.exists():
        return []
    manifests: list[Path] = []
    for path in outputs_dir.rglob(MANIFEST_GLOB):
        if any(part in ARCHIVE_DIR_NAMES for part in path.parts):
            continue
        manifests.append(path)
    return sorted(manifests, key=lambda p: p.stat().st_mtime, reverse=True)


def resolve_manifest_path(project_root: Path, path_string: str | None) -> Path | None:
    """Resolve an absolute or project-relative path from a manifest string."""
    if path_string is None:
        return None
    text = str(path_string).strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def path_for_manifest(path: Path | str | None, project_root: Path | None = None) -> str | None:
    """Store absolute path when possible for reliable Streamlit reload."""
    if path is None:
        return None
    text = str(path).strip()
    if not text:
        return None
    resolved = Path(text).resolve()
    return str(resolved)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def update_and_save_manifest(
    *,
    manifest_path: Path,
    case_id: str,
    timestamp: str,
    request_text: str,
    provider: str,
    model: str,
    planning_mode: str = "ai_direct",
    case_config_path: Path | str | None = None,
    understanding_spec_path: Path | str | None = None,
    module_selection_plan_path: Path | str | None = None,
    planning_spec_path: Path | str | None = None,
    requirement_workbook_path: Path | str | None = None,
    ppt_ready_workbook_path: Path | str | None = None,
    html_preview_path: Path | str | None = None,
    report_blueprint_path: Path | str | None = None,
    analysis_plan_path: Path | str | None = None,
    solve_loop_state_path: Path | str | None = None,
    solve_verdict_path: Path | str | None = None,
    data_workbook_path: Path | str | None = None,
    conclusion_brief_path: Path | str | None = None,
    conclusion_brief_json_path: Path | str | None = None,
    visual_report_spec_path: Path | str | None = None,
    html_report_path: Path | str | None = None,
    subset_scope_dir: Path | str | None = None,
    sub_l3_filter_spec_path: Path | str | None = None,
    sub_l3_filter_rules_path: Path | str | None = None,
    status: str = "in_progress",
    error_step: str | None = None,
    error_message: str | None = None,
    created_at: str | None = None,
) -> PipelineManifest:
    """Create/update a run manifest and persist it."""
    existing: PipelineManifest | None = None
    if manifest_path.exists():
        try:
            existing = load_pipeline_manifest(manifest_path)
        except Exception:
            existing = None

    created = created_at or (existing.created_at if existing and existing.created_at else utc_now_iso())
    manifest = PipelineManifest(
        case_id=case_id or (existing.case_id if existing else ""),
        timestamp=timestamp or (existing.timestamp if existing else ""),
        request_text=request_text if request_text is not None else (existing.request_text if existing else ""),
        provider=provider or (existing.provider if existing else ""),
        model=model or (existing.model if existing else ""),
        planning_mode=planning_mode or (existing.planning_mode if existing else "ai_direct"),
        case_config_path=path_for_manifest(case_config_path)
        if case_config_path is not None
        else (existing.case_config_path if existing else None),
        understanding_spec_path=path_for_manifest(understanding_spec_path)
        if understanding_spec_path is not None
        else (existing.understanding_spec_path if existing else None),
        module_selection_plan_path=path_for_manifest(module_selection_plan_path)
        if module_selection_plan_path is not None
        else (existing.module_selection_plan_path if existing else None),
        planning_spec_path=path_for_manifest(planning_spec_path)
        if planning_spec_path is not None
        else (existing.planning_spec_path if existing else None),
        requirement_workbook_path=path_for_manifest(requirement_workbook_path)
        if requirement_workbook_path is not None
        else (existing.requirement_workbook_path if existing else None),
        ppt_ready_workbook_path=path_for_manifest(ppt_ready_workbook_path)
        if ppt_ready_workbook_path is not None
        else (existing.ppt_ready_workbook_path if existing else None),
        html_preview_path=path_for_manifest(html_preview_path)
        if html_preview_path is not None
        else (existing.html_preview_path if existing else None),
        report_blueprint_path=path_for_manifest(report_blueprint_path)
        if report_blueprint_path is not None
        else (getattr(existing, "report_blueprint_path", None) if existing else None),
        analysis_plan_path=path_for_manifest(analysis_plan_path)
        if analysis_plan_path is not None
        else (getattr(existing, "analysis_plan_path", None) if existing else None),
        solve_loop_state_path=path_for_manifest(solve_loop_state_path)
        if solve_loop_state_path is not None
        else (getattr(existing, "solve_loop_state_path", None) if existing else None),
        solve_verdict_path=path_for_manifest(solve_verdict_path)
        if solve_verdict_path is not None
        else (getattr(existing, "solve_verdict_path", None) if existing else None),
        data_workbook_path=path_for_manifest(data_workbook_path)
        if data_workbook_path is not None
        else (getattr(existing, "data_workbook_path", None) if existing else None),
        conclusion_brief_path=path_for_manifest(conclusion_brief_path)
        if conclusion_brief_path is not None
        else (getattr(existing, "conclusion_brief_path", None) if existing else None),
        conclusion_brief_json_path=path_for_manifest(conclusion_brief_json_path)
        if conclusion_brief_json_path is not None
        else (getattr(existing, "conclusion_brief_json_path", None) if existing else None),
        visual_report_spec_path=path_for_manifest(visual_report_spec_path)
        if visual_report_spec_path is not None
        else (getattr(existing, "visual_report_spec_path", None) if existing else None),
        html_report_path=path_for_manifest(html_report_path)
        if html_report_path is not None
        else (getattr(existing, "html_report_path", None) if existing else None),
        subset_scope_dir=path_for_manifest(subset_scope_dir)
        if subset_scope_dir is not None
        else (getattr(existing, "subset_scope_dir", None) if existing else None),
        sub_l3_filter_spec_path=path_for_manifest(sub_l3_filter_spec_path)
        if sub_l3_filter_spec_path is not None
        else (getattr(existing, "sub_l3_filter_spec_path", None) if existing else None),
        sub_l3_filter_rules_path=path_for_manifest(sub_l3_filter_rules_path)
        if sub_l3_filter_rules_path is not None
        else (getattr(existing, "sub_l3_filter_rules_path", None) if existing else None),
        created_at=created,
        pipeline_version=PIPELINE_VERSION,
        status=status,
        error_step=error_step,
        error_message=error_message,
    )
    save_pipeline_manifest(manifest, manifest_path)
    return manifest


def register_subset_scope_artifacts(
    manifest_path: Path,
    output_dir: Path,
    *,
    state_metadata: dict[str, Any] | None = None,
) -> PipelineManifest | None:
    """Persist subset_scope artifact paths on manifest when files exist on disk."""
    subset_dir = output_dir / "subset_scope"
    manifest_file = subset_dir / MANIFEST_FILENAME
    if not manifest_file.exists():
        return None

    spec_path = subset_dir / FILTER_SPEC_FILENAME
    rules_path = subset_dir / FILTER_RULES_MD_FILENAME
    if state_metadata:
        subset_dir_text = state_metadata.get("subset_scope_dir")
        if subset_dir_text:
            subset_dir = Path(str(subset_dir_text))
        spec_text = state_metadata.get("sub_l3_filter_spec_path")
        if spec_text:
            spec_path = Path(str(spec_text))
        rules_text = state_metadata.get("sub_l3_filter_rules_path")
        if rules_text:
            rules_path = Path(str(rules_text))

    existing = load_pipeline_manifest(manifest_path)
    updated = PipelineManifest(
        case_id=existing.case_id,
        timestamp=existing.timestamp,
        request_text=existing.request_text,
        provider=existing.provider,
        model=existing.model,
        planning_mode=existing.planning_mode,
        case_config_path=existing.case_config_path,
        understanding_spec_path=existing.understanding_spec_path,
        module_selection_plan_path=existing.module_selection_plan_path,
        planning_spec_path=existing.planning_spec_path,
        requirement_workbook_path=existing.requirement_workbook_path,
        ppt_ready_workbook_path=existing.ppt_ready_workbook_path,
        html_preview_path=existing.html_preview_path,
        report_blueprint_path=existing.report_blueprint_path,
        analysis_plan_path=existing.analysis_plan_path,
        solve_loop_state_path=existing.solve_loop_state_path,
        solve_verdict_path=existing.solve_verdict_path,
        data_workbook_path=existing.data_workbook_path,
        conclusion_brief_path=existing.conclusion_brief_path,
        conclusion_brief_json_path=existing.conclusion_brief_json_path,
        visual_report_spec_path=existing.visual_report_spec_path,
        html_report_path=existing.html_report_path,
        subset_scope_dir=path_for_manifest(subset_dir),
        sub_l3_filter_spec_path=path_for_manifest(spec_path) if spec_path.exists() else existing.sub_l3_filter_spec_path,
        sub_l3_filter_rules_path=path_for_manifest(rules_path) if rules_path.exists() else existing.sub_l3_filter_rules_path,
        created_at=existing.created_at,
        pipeline_version=existing.pipeline_version,
        status=existing.status,
        error_step=existing.error_step,
        error_message=existing.error_message,
        extra=dict(existing.extra),
    )
    save_pipeline_manifest(updated, manifest_path)
    return updated
