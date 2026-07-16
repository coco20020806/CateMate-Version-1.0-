"""Load and query rawdata catalog (category / shop / item dimensions)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml

from catemate.core.paths import CONFIG_DIR, RAWDATA_GRAIN_DIRS

CatalogStatus = Literal["available", "missing"]
GrainType = Literal["category", "shop", "item"]

DEFAULT_CATALOG_PATH = CONFIG_DIR / "rawdata_catalog.yaml"


def load_rawdata_catalog(path: Path | None = None) -> dict[str, Any]:
    catalog_path = path or DEFAULT_CATALOG_PATH
    if not catalog_path.exists():
        return {"version": 1, "tables": []}
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid rawdata catalog: {catalog_path}")
    return payload


def list_catalog_tables(
    catalog: dict[str, Any] | None = None,
    *,
    grain: GrainType | None = None,
    status: CatalogStatus | None = None,
) -> list[dict[str, Any]]:
    catalog = catalog or load_rawdata_catalog()
    tables = catalog.get("tables") or []
    result: list[dict[str, Any]] = []
    for entry in tables:
        if not isinstance(entry, dict):
            continue
        if grain and entry.get("grain") != grain:
            continue
        if status and entry.get("status") != status:
            continue
        result.append(entry)
    return result


def get_catalog_entry(table_id: str, catalog: dict[str, Any] | None = None) -> dict[str, Any] | None:
    for entry in list_catalog_tables(catalog):
        if entry.get("table_id") == table_id:
            return entry
    return None


def catalog_key(grain: str, table_id: str) -> str:
    return f"{grain}/{table_id}"


def is_catalog_available(
    grain: str,
    table_id: str,
    catalog: dict[str, Any] | None = None,
    *,
    category_path: tuple[str, str, str] | None = None,
) -> bool:
    entry = get_catalog_entry(table_id, catalog)
    if entry is None:
        return False
    if entry.get("grain") != grain:
        return False

    resolution_mode = str(entry.get("resolution_mode") or "").strip()
    if grain == "item" or resolution_mode == "category_folder":
        from catemate.data.rawdata_loader import rawdata_available

        if category_path is None:
            return False
        l1, l2, l3 = category_path
        return rawdata_available(
            grain,
            table_id,
            category_l1=l1,
            category_l2=l2,
            category_l3=l3,
        )

    if grain == "category":
        from catemate.data.rawdata_workbook_loader import category_rawdata_available

        return category_rawdata_available(table_id)

    if grain == "shop":
        from catemate.core.paths import RAWDATA_SHOP_DIR
        from catemate.data.rawdata_loader import rawdata_available

        if entry.get("status") != "available":
            return rawdata_available(grain, table_id, search_dir=RAWDATA_SHOP_DIR)
        return rawdata_available(grain, table_id, search_dir=RAWDATA_SHOP_DIR)

    return entry.get("status") == "available"


def missing_catalog_entries(
    required: list[tuple[str, str]],
    catalog: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return catalog entries that are missing for (grain, table_id) pairs."""
    catalog = catalog or load_rawdata_catalog()
    missing: list[dict[str, Any]] = []
    for grain, table_id in required:
        entry = get_catalog_entry(table_id, catalog)
        if entry is None or entry.get("status") != "available" or entry.get("grain") != grain:
            missing.append(
                entry
                or {
                    "table_id": table_id,
                    "grain": grain,
                    "status": "missing",
                    "description": f"未登记的源表 {grain}/{table_id}",
                }
            )
    return missing


def resolve_rawdata_search_dirs(grain: str | None = None) -> list[Path]:
    if grain and grain in RAWDATA_GRAIN_DIRS:
        return [RAWDATA_GRAIN_DIRS[grain]]  # type: ignore[index]
    return list(RAWDATA_GRAIN_DIRS.values())


def update_catalog_status(
    table_id: str,
    status: CatalogStatus,
    *,
    catalog_path: Path | None = None,
    file_path: str = "",
) -> dict[str, Any]:
    catalog_path = catalog_path or DEFAULT_CATALOG_PATH
    catalog = load_rawdata_catalog(catalog_path)
    tables = catalog.setdefault("tables", [])
    for entry in tables:
        if isinstance(entry, dict) and entry.get("table_id") == table_id:
            entry["status"] = status
            if file_path:
                entry["file_path"] = file_path
            break
    else:
        tables.append({"table_id": table_id, "status": status, "file_path": file_path})
    with catalog_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(catalog, file, allow_unicode=True, sort_keys=False)
    return catalog


def save_rawdata_catalog(catalog: dict[str, Any], path: Path | None = None) -> Path:
    catalog_path = path or DEFAULT_CATALOG_PATH
    with catalog_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(catalog, file, allow_unicode=True, sort_keys=False)
    return catalog_path
