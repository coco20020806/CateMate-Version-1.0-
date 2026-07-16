"""Unified rawdata loading across category / shop / item grains."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from catemate.core.paths import RAWDATA_GRAIN_DIRS, RAWDATA_ITEM_DIR
from catemate.data.rawdata_catalog import get_catalog_entry
from catemate.data.rawdata_workbook_loader import (
    category_rawdata_available,
    load_category_rawdata_table,
)

ITEM_CSV_REQUIRED_COLUMNS = {
    "grass_month",
    "grass_region",
    "gmv_usd",
    "orders",
}


def rawdata_available(
    grain: str,
    table_id: str,
    *,
    category_l1: str = "",
    category_l2: str = "",
    category_l3: str = "",
    search_dir: Path | None = None,
) -> bool:
    try:
        _resolve_rawdata_source(
            grain,
            table_id,
            category_l1=category_l1,
            category_l2=category_l2,
            category_l3=category_l3,
            search_dir=search_dir,
        )
        return True
    except (FileNotFoundError, ValueError):
        return False


def load_rawdata_table(
    grain: str,
    table_id: str,
    *,
    category_l1: str = "",
    category_l2: str = "",
    category_l3: str = "",
    search_dir: Path | None = None,
    sheet_name: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    resolution = _resolve_rawdata_source(
        grain,
        table_id,
        category_l1=category_l1,
        category_l2=category_l2,
        category_l3=category_l3,
        search_dir=search_dir,
    )
    if resolution["loader"] == "category_folder":
        return _load_item_category_folder_csv(resolution)
    return load_category_rawdata_table(
        table_id,
        search_dir=resolution["search_dir"],
        sheet_name=sheet_name,
    )


def _resolve_rawdata_source(
    grain: str,
    table_id: str,
    *,
    category_l1: str = "",
    category_l2: str = "",
    category_l3: str = "",
    search_dir: Path | None = None,
) -> dict:
    entry = get_catalog_entry(table_id) or {}
    if entry.get("grain") and entry.get("grain") != grain:
        raise ValueError(f"table_id={table_id} grain mismatch: expected {grain}, got {entry.get('grain')}")

    resolution_mode = str(entry.get("resolution_mode") or "").strip()
    if grain == "item" or resolution_mode == "category_folder":
        folder = _resolve_item_category_folder(
            category_l1=category_l1,
            category_l2=category_l2,
            category_l3=category_l3,
        )
        files = _list_item_csv_files(folder)
        if not files:
            raise FileNotFoundError(f"No item CSV files under {folder}")
        return {
            "loader": "category_folder",
            "folder": folder,
            "files": files,
            "table_id": table_id,
        }

    grain_dir = search_dir or RAWDATA_GRAIN_DIRS.get(grain)
    if grain_dir is None:
        raise ValueError(f"Unsupported rawdata grain: {grain}")
    if grain == "category":
        if not category_rawdata_available(table_id, search_dir=grain_dir):
            raise FileNotFoundError(f"No category workbook for table_id={table_id} under {grain_dir}")
    elif grain == "shop":
        if not _flat_workbook_available(table_id, search_dir=grain_dir):
            raise FileNotFoundError(f"No shop workbook for table_id={table_id} under {grain_dir}")
    return {
        "loader": "flat_workbook",
        "search_dir": grain_dir,
        "table_id": table_id,
    }


def _flat_workbook_available(table_id: str, *, search_dir: Path) -> bool:
    if not search_dir.is_dir():
        return False
    return bool(list(search_dir.glob("*.xlsx")))


def _resolve_item_category_folder(
    *,
    category_l1: str,
    category_l2: str,
    category_l3: str,
) -> Path:
    l1 = category_l1.strip()
    l2 = category_l2.strip()
    l3 = category_l3.strip()
    if not (l1 and l2 and l3):
        raise ValueError("item grain requires category_l1, category_l2, and category_l3")
    folder = RAWDATA_ITEM_DIR / l1 / l2 / l3
    if not folder.is_dir():
        raise FileNotFoundError(f"Item category folder not found: {folder}")
    return folder


def _list_item_csv_files(folder: Path) -> list[Path]:
    files = sorted(folder.glob("*.csv"), key=lambda path: path.name.lower())
    return [path for path in files if path.is_file()]


def _load_item_category_folder_csv(resolution: dict) -> tuple[pd.DataFrame, dict]:
    files: list[Path] = resolution["files"]
    folder: Path = resolution["folder"]
    frames: list[pd.DataFrame] = []
    for path in files:
        frame = pd.read_csv(path)
        frame.columns = [str(col).strip() for col in frame.columns]
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No readable CSV files under {folder}")
    df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    missing = ITEM_CSV_REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Item CSV under {folder} missing required columns: {sorted(missing)}"
        )
    meta = {
        "table_id": resolution["table_id"],
        "csv_path": str(folder),
        "files": [str(path) for path in files],
        "row_count": len(df),
        "columns": list(df.columns),
        "source": "rawdata_item_csv",
    }
    return df, meta
