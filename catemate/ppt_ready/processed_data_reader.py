"""Read processed manifest and CSV tables without touching raw Excel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def load_processed_manifest(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to read processed_manifest.yaml. Install with `pip install PyYAML`."
        ) from exc

    if not path.exists():
        raise FileNotFoundError(f"processed manifest not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid processed manifest (expected mapping): {path}")
    return payload


def get_table_entry(manifest: dict[str, Any], table_id: str) -> dict[str, Any] | None:
    tables = manifest.get("tables") or []
    if not isinstance(tables, list):
        return None
    for entry in tables:
        if isinstance(entry, dict) and str(entry.get("table_id", "")) == table_id:
            return entry
    return None


def resolve_processed_csv_path(
    table_entry: dict[str, Any],
    processed_data_dir: Path | None = None,
) -> Path:
    """Resolve CSV path from manifest entry. Prefer absolute output_csv."""
    output_csv = str(table_entry.get("output_csv") or "").strip()
    if output_csv:
        path = Path(output_csv)
        if path.is_absolute() and path.exists():
            return path
        if path.is_absolute():
            # Absolute path recorded but missing — fall through to relative.
            pass
        elif processed_data_dir is not None:
            candidate = (processed_data_dir / path).resolve()
            if candidate.exists():
                return candidate

    relative = str(table_entry.get("output_csv_relative") or "").strip()
    if relative and processed_data_dir is not None:
        candidate = (processed_data_dir / relative).resolve()
        if candidate.exists():
            return candidate

    table_id = table_entry.get("table_id", "<unknown>")
    raise FileNotFoundError(
        f"Processed CSV not found for table_id={table_id}. "
        f"Checked output_csv={output_csv!r}, output_csv_relative={relative!r}."
    )


def _display_csv_path(path: Path, project_root: Path | None) -> str:
    if project_root is not None:
        try:
            return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
        except ValueError:
            pass
    return path.name


def get_table_lineage(
    manifest: dict[str, Any],
    table_id: str,
    processed_data_dir: Path,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Return source lineage for a table_id from processed manifest only."""
    entry = get_table_entry(manifest, table_id)
    if entry is None:
        return {
            "table_id": table_id,
            "error": "table_id not found in processed_manifest",
            "source_workbook_name": "",
            "source_sheet": "",
            "processed_csv_path": "",
            "row_count": None,
            "columns": [],
        }

    csv_display = ""
    try:
        csv_path = resolve_processed_csv_path(entry, processed_data_dir=processed_data_dir)
        csv_display = _display_csv_path(csv_path, project_root)
    except Exception as exc:
        relative = str(entry.get("output_csv_relative") or "").strip()
        if relative:
            csv_display = relative.replace("\\", "/")
        else:
            csv_display = f"<unresolved: {exc}>"

    columns = entry.get("columns") or []
    if not isinstance(columns, list):
        columns = []

    return {
        "table_id": table_id,
        "source_workbook_name": str(entry.get("source_workbook_name") or ""),
        "source_sheet": str(entry.get("source_sheet") or ""),
        "processed_csv_path": csv_display,
        "row_count": entry.get("row_count"),
        "columns": [str(c) for c in columns],
    }


def load_processed_table(
    table_entry: dict[str, Any],
    processed_data_dir: Path | None = None,
) -> pd.DataFrame:
    csv_path = resolve_processed_csv_path(table_entry, processed_data_dir=processed_data_dir)
    return pd.read_csv(csv_path, low_memory=False)
