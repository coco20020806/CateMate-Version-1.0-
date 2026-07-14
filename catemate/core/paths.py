"""Per-run output directory helpers."""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "CateMate_rawdata"
PROCESSED_DATA_DIR = PROJECT_ROOT / "CateMate_processeddata"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
OUTPUTS_RUNS_DIR = OUTPUTS_DIR / "runs"
OUTPUTS_LEGACY_DIR = OUTPUTS_DIR / "_legacy"
# Deprecated alias kept for older imports; new runs live under outputs/runs/.
RUNS_DIR = OUTPUTS_RUNS_DIR
CONFIG_DIR = PROJECT_ROOT / "config"

ARCHIVE_DIR_NAMES = {"_legacy", "_quarantine", "_trash"}


def _safe_run_slug(case_id: str) -> str:
    text = (case_id or "unknown_case").strip() or "unknown_case"
    safe = re.sub(r"[^a-zA-Z0-9_\-]+", "_", text)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "unknown_case"


def pipeline_run_dir(case_id: str, timestamp: str, *, base: Path | None = None) -> Path:
    """Directory for one pipeline run: outputs/runs/<case_id>_<timestamp>/."""
    root = base or OUTPUTS_DIR
    return root / "runs" / f"{_safe_run_slug(case_id)}_{timestamp}"


def is_default_outputs_root(path: Path) -> bool:
    return path.resolve() == OUTPUTS_DIR.resolve()


def resolve_new_run_output_dir(case_id: str, timestamp: str, output_dir: Path) -> Path:
    """When caller uses default outputs root, allocate outputs/runs/<case_id>_<timestamp>/."""
    if is_default_outputs_root(output_dir):
        run_dir = pipeline_run_dir(case_id, timestamp, base=output_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
    return output_dir


def ensure_project_dirs() -> None:
    """Create runtime directories used by CateMate."""
    for path in (
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        OUTPUTS_DIR,
        OUTPUTS_RUNS_DIR,
        OUTPUTS_LEGACY_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
