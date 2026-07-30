"""Forced fuzzy display rules for print_vertical_report."""

from __future__ import annotations

import math
import re
from typing import Any

from catemate.print_report.schemas import FuzzyMetric, MetricKind

PERCENT_HINTS = ("pct", "percent", "share", "ratio", "rate", "mom", "yoy", "占比", "环比", "同比")
MONEY_HINTS = ("gmv", "adg", "adgmv", "usd", "revenue", "sales", "金额")
ORDERS_HINTS = ("order", "ado", "单量", "orders")


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def infer_metric_kind(label: str, *, value: Any = None) -> MetricKind:
    text = (label or "").strip().lower()
    if any(hint in text for hint in PERCENT_HINTS):
        return "percent"
    if any(hint in text for hint in MONEY_HINTS):
        return "money"
    if any(hint in text for hint in ORDERS_HINTS):
        return "orders"
    number = _to_float(value)
    if number is not None and abs(number) <= 1.5 and ("share" in text or "pct" in text):
        return "percent"
    return "other"


def fuzzy_percent(value: Any) -> str:
    """Map a ratio or percent number to a 10%-step bucket."""
    number = _to_float(value)
    if number is None:
        return "—"
    # Accept both 0.12 and 12 as percent inputs.
    pct = number * 100 if abs(number) <= 1.5 else number
    if pct < 5:
        return "<5%"
    if pct > 100:
        return ">100%"
    low = int(pct // 10) * 10
    high = low + 10
    if low == 0:
        low = 0
    return f"{low}%-{high}%"


def fuzzy_money(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "—"
    amount = abs(number)
    if amount < 5_000:
        return "<$5K"
    if amount < 50_000:
        return "$5K-$50K"
    if amount < 200_000:
        return "$50K-$200K"
    if amount < 1_000_000:
        return "$200K-$1M"
    if amount < 5_000_000:
        return "$1M-$5M"
    return ">$5M"


def fuzzy_orders(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "—"
    amount = abs(number)
    if amount < 100:
        return "<100"
    if amount < 1_000:
        return "100-1K"
    if amount < 10_000:
        return "1K-10K"
    if amount < 50_000:
        return "10K-50K"
    if amount < 200_000:
        return "50K-200K"
    return ">200K"


def format_price_range_label(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    match = re.match(r"^\d{1,3}_(.+)$", text)
    if match:
        return match.group(1)
    return text


def fuzzy_metric(label: str, value: Any, *, kind: MetricKind | None = None) -> FuzzyMetric:
    resolved = kind or infer_metric_kind(label, value=value)
    if resolved == "percent":
        display = fuzzy_percent(value)
    elif resolved == "money":
        display = fuzzy_money(value)
    elif resolved == "orders":
        display = fuzzy_orders(value)
    elif resolved == "label":
        display = format_price_range_label(value) or ("" if value is None else str(value))
        return FuzzyMetric(label=label, display=display, kind=resolved, raw_suppressed=False)
    else:
        # Unknown numeric → money-like magnitude to avoid leaking exacts.
        number = _to_float(value)
        display = fuzzy_money(number) if number is not None else ("" if value is None else str(value))
        resolved = "money" if number is not None else "other"
    return FuzzyMetric(label=label, display=display, kind=resolved, raw_suppressed=True)


def relative_share(values: list[float]) -> list[float]:
    """Normalize to 0-100 relative widths for CSS charts (no absolute labels)."""
    cleaned = [max(0.0, float(v)) for v in values]
    total = sum(cleaned)
    if total <= 0:
        return [0.0 for _ in cleaned]
    return [round(v / total * 100.0, 2) for v in cleaned]
