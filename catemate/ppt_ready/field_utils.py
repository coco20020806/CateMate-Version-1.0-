"""Shared field helpers for PPT-ready builder and HTML preview."""

from __future__ import annotations

import math
import re
from typing import Any, Iterable


MONTH_TIME_FIELDS = ["grass_month", "year_month", "month", "date", "grass_date"]
DAILY_TIME_FIELDS = ["grass_date", "date", "grass_month", "year_month", "month"]


def is_daily_context(
    *,
    table_ids: Iterable[str] | None = None,
    source_sheets: Iterable[str] | None = None,
    chart_id: str = "",
    chart_title: str = "",
    grain: str = "",
    force_monthly: bool = False,
) -> bool:
    """Heuristically detect daily trend charts that should use grass_date."""
    if force_monthly:
        return False
    tables = {str(t).strip().lower() for t in (table_ids or []) if t}
    sheets = {str(s).strip().lower() for s in (source_sheets or []) if s}
    text = f"{chart_id} {chart_title} {grain}".lower()
    if "dashboard_daily_data" in tables:
        return True
    if any("daily data" == s or s.endswith("daily data") for s in sheets):
        return True
    if "daily" in text or "日度" in text:
        return True
    return False


def resolve_trend_time_fields(
    *,
    table_ids: Iterable[str] | None = None,
    source_sheets: Iterable[str] | None = None,
    chart_id: str = "",
    chart_title: str = "",
    grain: str = "",
    preferred_from_chart: list[str] | None = None,
    force_monthly: bool = False,
) -> tuple[list[str], bool, str]:
    """Return ordered candidate time fields and whether this is daily context."""
    daily = is_daily_context(
        table_ids=table_ids,
        source_sheets=source_sheets,
        chart_id=chart_id,
        chart_title=chart_title,
        grain=grain,
        force_monthly=force_monthly,
    )
    extras = [
        d
        for d in (preferred_from_chart or [])
        if "month" in d.lower() or "date" in d.lower()
    ]
    if daily:
        ordered = []
        for name in DAILY_TIME_FIELDS + extras:
            if name not in ordered:
                ordered.append(name)
        note = "daily data preview uses grass_date instead of month"
        return ordered, True, note
    ordered = []
    for name in MONTH_TIME_FIELDS + extras:
        if name not in ordered:
            ordered.append(name)
    return ordered, False, ""


def price_range_sort_key(value: Any) -> tuple:
    """Natural sort key for Price_Range_USD labels.

    Supports current processed formats like:
    - 01_[0,1)
    - 02_[1,2)
    - 09_[20,Inf)
    and plain variants like [0,1], 0-1, >=1, 1+.
    """
    if value is None:
        return (2, math.inf, math.inf, "")
    text = str(value).strip()
    if not text:
        return (2, math.inf, math.inf, "")

    # Prefer leading index prefix used by dashboard_price_tier: "01_[0,1)"
    prefix = re.match(r"^(\d{1,3})_", text)
    if prefix:
        return (0, int(prefix.group(1)), 0.0, text)

    normalized = text.replace("～", "~").replace("—", "-").replace("–", "-")
    normalized = normalized.replace(" ", "")

    # >=1 / 1+ / Inf open-ended
    open_end = re.match(r"^(?:>=|>)?\s*(\d+(?:\.\d+)?)\+?$", normalized, re.I)
    if open_end:
        return (1, float(open_end.group(1)), math.inf, text)

    if re.search(r"inf", normalized, re.I):
        nums = re.findall(r"\d+(?:\.\d+)?", normalized)
        low = float(nums[0]) if nums else math.inf
        return (1, low, math.inf, text)

    # Bracket/range forms: [0,1), (0,1], 0-1, 0~1
    nums = re.findall(r"\d+(?:\.\d+)?", normalized)
    if len(nums) >= 2:
        return (1, float(nums[0]), float(nums[1]), text)
    if len(nums) == 1:
        return (1, float(nums[0]), float(nums[0]), text)
    return (2, math.inf, math.inf, text)


def sort_by_price_range(items: list[tuple[str, Any]]) -> list[tuple[str, Any]]:
    """Sort (label, value) pairs by Price_Range_USD natural order."""
    return sorted(items, key=lambda item: price_range_sort_key(item[0]))


def looks_like_gmv_orders_trend(metrics: Iterable[str] | None, title: str = "") -> bool:
    names = {str(m).lower() for m in (metrics or [])}
    text = title.lower()
    has_gmv = any("gmv" in n or n == "adg" for n in names) or "gmv" in text
    has_orders = any("order" in n or n == "ado" for n in names) or "order" in text
    return has_gmv or has_orders or "aov" in text or "趋势" in title
