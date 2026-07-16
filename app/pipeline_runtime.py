"""Run pipeline / PPT-ready steps in a fresh subprocess to avoid Streamlit module-cache issues."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from catemate.pipeline.manifest import load_pipeline_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_CLI_SCRIPT = PROJECT_ROOT / "scripts" / "run_natural_language_requirement_pipeline.py"
PPT_READY_CLI_SCRIPT = PROJECT_ROOT / "scripts" / "build_ppt_ready_from_confirmed_workbook.py"

PIPELINE_RUNTIME_MODULES = (
    "catemate.pipeline.runner",
    "catemate.case_generation.generator",
    "catemate.case_generation.confirmation_enrichment",
)


def reset_pipeline_runtime_modules() -> None:
    """Drop cached pipeline modules so the next import reads code from disk."""
    to_remove = [
        name
        for name in list(sys.modules)
        if name in PIPELINE_RUNTIME_MODULES or name.startswith("catemate.pipeline.runner.")
    ]
    for name in to_remove:
        sys.modules.pop(name, None)


def _parse_manifest_path_from_output(stdout: str) -> Path | None:
    for line in stdout.splitlines():
        if line.startswith("pipeline_manifest_path:"):
            raw = line.split(":", 1)[1].strip()
            if raw:
                return Path(raw)
    return None


def _result_from_subprocess(
    *,
    proc: subprocess.CompletedProcess[str],
    manifest_path: Path | None = None,
):
    from catemate.pipeline.runner import PipelineRunResult

    resolved_manifest = manifest_path or _parse_manifest_path_from_output(proc.stdout or "")
    if proc.returncode == 0 and resolved_manifest is not None and resolved_manifest.exists():
        manifest = load_pipeline_manifest(resolved_manifest)
        return PipelineRunResult(exit_code=0, manifest_path=resolved_manifest, manifest=manifest)

    message = (proc.stderr or proc.stdout or "").strip() or "Pipeline 运行失败。"
    return PipelineRunResult(
        exit_code=proc.returncode or 1,
        manifest_path=resolved_manifest,
        error_message=message,
    )


def run_pipeline_continue_after_category_confirmation_subprocess(manifest_path: Path):
    """Resume pipeline after category confirmation in a fresh subprocess."""
    manifest_path = Path(manifest_path)
    proc = subprocess.run(
        [
            sys.executable,
            str(PIPELINE_CLI_SCRIPT),
            "--continue-after-category-confirmation",
            str(manifest_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    return _result_from_subprocess(proc=proc, manifest_path=manifest_path)


def run_pipeline_continue_from_manifest_subprocess(manifest_path: Path):
    """Resume pipeline in a fresh Python process (immune to Streamlit sys.modules cache)."""
    manifest_path = Path(manifest_path)
    proc = subprocess.run(
        [
            sys.executable,
            str(PIPELINE_CLI_SCRIPT),
            "--continue-from-manifest",
            str(manifest_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    return _result_from_subprocess(proc=proc, manifest_path=manifest_path)


def run_pipeline_from_request_text_subprocess(
    *,
    request_text: str,
    planning_mode: str,
):
    """Start pipeline from natural language in a fresh Python process."""
    proc = subprocess.run(
        [
            sys.executable,
            str(PIPELINE_CLI_SCRIPT),
            "--request-text",
            request_text,
            "--planning-mode",
            planning_mode,
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    return _result_from_subprocess(proc=proc)


@dataclass
class PptReadySubprocessResult:
    exit_code: int
    case_id: str = ""
    output_path: Path | None = None
    html_preview_path: Path | None = None
    sheet_count: int = 0
    warning_count: int = 0
    gate_message: str = ""
    error_message: str = ""


def _parse_kv_output(stdout: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in stdout.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        values[key.strip()] = raw.strip()
    return values


def run_ppt_ready_subprocess(
    *,
    requirement_workbook: Path,
    planning_spec_path: Path,
    pipeline_manifest_path: Path | None = None,
    processed_manifest_path: Path | None = None,
    processed_data_dir: Path | None = None,
) -> PptReadySubprocessResult:
    """Build PPT-ready workbook + HTML preview in a fresh Python process."""
    cmd = [
        sys.executable,
        str(PPT_READY_CLI_SCRIPT),
        "--requirement-workbook",
        str(requirement_workbook),
        "--planning-spec",
        str(planning_spec_path),
    ]
    if pipeline_manifest_path is not None:
        cmd.extend(["--pipeline-manifest", str(pipeline_manifest_path)])
    if processed_manifest_path is not None:
        cmd.extend(["--processed-manifest", str(processed_manifest_path)])
    if processed_data_dir is not None:
        cmd.extend(["--processed-data-dir", str(processed_data_dir)])

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    values = _parse_kv_output(proc.stdout or "")
    if proc.returncode == 0:
        html_raw = values.get("html_preview")
        return PptReadySubprocessResult(
            exit_code=0,
            case_id=values.get("case_id", ""),
            output_path=Path(values["output"]) if values.get("output") else None,
            html_preview_path=Path(html_raw) if html_raw else None,
            sheet_count=int(values.get("sheet_count") or 0),
            warning_count=int(values.get("warning_count") or 0),
            gate_message="confirmation_gate: passed",
        )

    message = (proc.stderr or proc.stdout or "").strip() or "PPT-ready 生成失败。"
    return PptReadySubprocessResult(exit_code=proc.returncode or 1, error_message=message)
