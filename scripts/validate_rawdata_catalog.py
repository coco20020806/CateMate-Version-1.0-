"""Validate rawdata catalog entries against files on disk."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from catemate.core.paths import RAWDATA_CATEGORY_DIR, RAWDATA_ITEM_DIR
from catemate.data.rawdata_catalog import list_catalog_tables, load_rawdata_catalog
from catemate.data.rawdata_loader import rawdata_available
from catemate.data.rawdata_workbook_loader import category_rawdata_available


def main() -> int:
    errors: list[str] = []
    catalog = load_rawdata_catalog()

    for entry in list_catalog_tables(catalog, status="available"):
        table_id = str(entry.get("table_id") or "").strip()
        grain = str(entry.get("grain") or "").strip()
        if not table_id or not grain:
            continue

        if grain == "category":
            if not category_rawdata_available(table_id, search_dir=RAWDATA_CATEGORY_DIR):
                errors.append(
                    f"CATEGORY_MISSING table_id={table_id} expected under {RAWDATA_CATEGORY_DIR}"
                )
        elif grain == "item":
            if str(entry.get("resolution_mode") or "") != "category_folder":
                if not rawdata_available(grain, table_id):
                    errors.append(f"ITEM_MISSING table_id={table_id}")
        elif grain == "shop":
            if not rawdata_available(grain, table_id):
                errors.append(f"SHOP_MISSING table_id={table_id}")

    if not RAWDATA_ITEM_DIR.is_dir():
        errors.append(f"ITEM_ROOT_MISSING {RAWDATA_ITEM_DIR}")

    if errors:
        for item in errors:
            print(f"ERROR {item}")
        return 1

    available = [str(e.get('table_id')) for e in list_catalog_tables(catalog, status="available")]
    print(f"OK rawdata_catalog available entries checked: {len(available)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
