"""Load category-grain workbooks directly from CateMate_rawdata (no processed CSV)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from catemate.core.paths import RAWDATA_CATEGORY_DIR
from catemate.data.rawdata_catalog import get_catalog_entry

CATEGORY_MONTHLY_COLUMNS = {
    "grass_region",
    "cb_level1_global_be_category",
    "level2_global_be_category",
    "level3_global_be_category",
    "grass_month",
    "gmv_usd",
    "orders",
}

TABLE_WORKBOOK_HINTS: dict[str, list[str]] = {
    "dashboard_history": ["monthly", "品类", "category"],
    "rm_raw_data": ["rm", "monthly", "品类", "category"],
    "dashboard_daily_data": ["daily", "日"],
    "dashboard_price_tier": ["price", "tier", "价格"],
    "dashboard_keywords": ["keyword", "关键词"],
    "dashboard_top_listing": ["listing", "商品"],
}


def category_rawdata_available(table_id: str, *, search_dir: Path | None = None) -> bool:
    try:
        _resolve_category_workbook(table_id, search_dir=search_dir)
        return True
    except FileNotFoundError:
        return False


def load_category_rawdata_table(
    table_id: str,
    *,
    search_dir: Path | None = None,
    sheet_name: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    workbook_path, resolved_sheet = _resolve_category_workbook(
        table_id,
        search_dir=search_dir,
        sheet_name=sheet_name,
    )
    df = pd.read_excel(workbook_path, sheet_name=resolved_sheet)
    df.columns = [str(col).strip() for col in df.columns]
    missing = CATEGORY_MONTHLY_COLUMNS - set(df.columns)
    if missing and table_id in {"dashboard_history", "rm_raw_data"}:
        raise ValueError(
            f"Workbook {workbook_path.name} sheet {resolved_sheet} missing columns: {sorted(missing)}"
        )
    meta = {
        "table_id": table_id,
        "csv_path": str(workbook_path),
        "sheet_name": resolved_sheet,
        "row_count": len(df),
        "columns": list(df.columns),
        "source": "rawdata_workbook",
    }
    return df, meta


def _resolve_category_workbook(
    table_id: str,
    *,
    search_dir: Path | None = None,
    sheet_name: str | None = None,
) -> tuple[Path, str]:
    search_dir = search_dir or RAWDATA_CATEGORY_DIR
    if not search_dir.is_dir():
        raise FileNotFoundError(f"Category rawdata directory not found: {search_dir}")

    catalog_entry = get_catalog_entry(table_id) or {}
    explicit_path = str(catalog_entry.get("file_path") or "").strip()
    if explicit_path:
        path = Path(explicit_path)
        if path.exists():
            return path, _resolve_sheet_name(path, sheet_name, catalog_entry)

    hints = list(TABLE_WORKBOOK_HINTS.get(table_id, []))
    hints.extend(_keywords_from_table_id(table_id))
    candidates = sorted(search_dir.glob("*.xlsx"))
    if not candidates:
        raise FileNotFoundError(f"No category workbooks under {search_dir}")

    ranked = sorted(
        candidates,
        key=lambda path: _workbook_rank(path, hints),
        reverse=True,
    )
    best = ranked[0]
    if _workbook_rank(best, hints) <= 0 and table_id in {"dashboard_history", "rm_raw_data"}:
        # Generic fallback: first workbook that contains monthly category columns.
        for path in candidates:
            try:
                sheet = _resolve_sheet_name(path, sheet_name, catalog_entry)
                preview = pd.read_excel(path, sheet_name=sheet, nrows=1)
                preview.columns = [str(col).strip() for col in preview.columns]
                if CATEGORY_MONTHLY_COLUMNS.issubset(set(preview.columns)):
                    return path, sheet
            except Exception:
                continue
        raise FileNotFoundError(
            f"No category monthly workbook with required columns for table_id={table_id} under {search_dir}"
        )
    return best, _resolve_sheet_name(best, sheet_name, catalog_entry)


def _resolve_sheet_name(path: Path, sheet_name: str | None, catalog_entry: dict) -> str:
    import pandas as pd

    if sheet_name:
        return sheet_name
    configured = str(catalog_entry.get("source_sheet") or "").strip()
    xl = pd.ExcelFile(path)
    if configured and configured in xl.sheet_names:
        return configured
    for candidate in ("Sheet1", "过去数据", "Raw data", "history"):
        if candidate in xl.sheet_names:
            return candidate
    return xl.sheet_names[0]


def _workbook_rank(path: Path, hints: list[str]) -> int:
    name = path.name.lower()
    score = 0
    for hint in hints:
        token = hint.lower().strip()
        if token and token in name:
            score += 2
    if re.search(r"monthly|month|月度|品类", name, flags=re.IGNORECASE):
        score += 1
    return score


def _keywords_from_table_id(table_id: str) -> list[str]:
    return [part for part in re.split(r"[_\-]+", table_id) if part]
