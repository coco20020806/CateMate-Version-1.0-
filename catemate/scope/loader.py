"""Load processed tables for Scope executor."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from catemate.core.paths import PROCESSED_DATA_DIR
from catemate.data.rawdata_catalog import get_catalog_entry, is_catalog_available
from catemate.data.rawdata_loader import load_rawdata_table
from catemate.ppt_ready.processed_data_reader import (
    get_table_entry,
    load_processed_manifest,
    load_processed_table,
    resolve_processed_csv_path,
)

RAWDATA_GRAINS = {"category", "shop", "item"}


def load_table_for_scope(
    table_id: str,
    *,
    grain: str = "",
    category_l1: str = "",
    category_l2: str = "",
    category_l3: str = "",
    processed_data_dir: Path | None = None,
    manifest_path: Path | None = None,
    prefer_rawdata: bool = True,
    require_rawdata: bool = False,
) -> tuple[pd.DataFrame, dict]:
    category_path = (category_l1, category_l2, category_l3)
    if prefer_rawdata and grain in RAWDATA_GRAINS:
        entry = get_catalog_entry(table_id) or {}
        entry_grain = str(entry.get("grain") or grain).strip()
        if entry_grain == grain and is_catalog_available(
            grain,
            table_id,
            category_path=category_path if grain == "item" else None,
        ):
            try:
                return load_rawdata_table(
                    grain,
                    table_id,
                    category_l1=category_l1,
                    category_l2=category_l2,
                    category_l3=category_l3,
                )
            except (FileNotFoundError, ValueError):
                if grain in {"category", "item"} or require_rawdata:
                    raise

        if require_rawdata and grain in {"category", "item"}:
            raise FileNotFoundError(
                f"Rawdata required for {grain}/{table_id} but catalog source is unavailable"
            )

    if require_rawdata and grain in {"category", "item"}:
        raise FileNotFoundError(
            f"Rawdata required for {grain}/{table_id}; processed CSV fallback is disabled"
        )

    processed_data_dir = processed_data_dir or PROCESSED_DATA_DIR
    manifest_path = manifest_path or (processed_data_dir / "processed_manifest.yaml")
    manifest = load_processed_manifest(manifest_path)
    entry = get_table_entry(manifest, table_id)
    if entry is None:
        raise FileNotFoundError(f"processed manifest missing table_id={table_id}")
    df = load_processed_table(entry, processed_data_dir=processed_data_dir)
    csv_path = resolve_processed_csv_path(entry, processed_data_dir)
    meta = {
        "table_id": table_id,
        "csv_path": str(csv_path),
        "row_count": len(df),
        "columns": list(df.columns),
        "source": "processed_csv",
    }
    return df, meta
