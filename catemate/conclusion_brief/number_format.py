"""Approximate numeric display rules for conclusion briefs.

Derived from conclusion-brief number patterns (orders, GMV, share, AOV, counts).
"""

from __future__ import annotations

import re
from typing import Literal

NumberKind = Literal[
    "volume",       # orders / GMV / large counts -> Nk
    "share",        # 0-1 fraction -> N%
    "mom_pct",      # small fraction change -> N.N%
    "aov",          # unit price -> 1 decimal
    "count",        # row/table counts -> integer
    "identifier",   # shop_id etc. -> keep exact
    "small",        # <1000 non-special -> integer or 1 decimal
]

# Do not rewrite numbers that already look formatted.
_ALREADY_FORMATTED = re.compile(r"[kK%]$")

# Match plain numeric tokens in prose (not inside words or backticks).
_NUMBER_TOKEN = re.compile(
    r"(?<![\w./])"
    r"(-?\d+(?:\.\d+)?)"
    r"(?![\w./])"
)

_ID_THRESHOLD = 100_000_000
_VOLUME_K_THRESHOLD = 1_000


def infer_number_kind(*, value: float, unit: str = "") -> NumberKind:
    """Infer formatting kind from numeric value and optional unit label."""
    unit_norm = unit.strip().lower().replace("-", "_")

    if unit_norm in {"shop_id", "item_id", "id"}:
        return "identifier"
    if unit_norm in {"rows", "row", "rank"}:
        return "count"
    if unit_norm in {"pct", "percent", "percentage"}:
        return "mom_pct" if abs(value) <= 1 else "small"
    if unit_norm in {"share", "ratio"}:
        return "share" if abs(value) <= 1 else "small"
    if unit_norm in {"usd/order", "usd_per_order", "aov"}:
        return "aov"
    if unit_norm in {"orders", "order", "usd", "gmv", "gmv_usd"}:
        if abs(value) >= _VOLUME_K_THRESHOLD:
            return "volume"
        return "small"

    if abs(value) >= _ID_THRESHOLD:
        return "identifier"
    if 0 < abs(value) < 1:
        return "mom_pct" if abs(value) < 0.3 else "share"
    if abs(value) >= _VOLUME_K_THRESHOLD:
        return "volume"
    if float(value).is_integer() and abs(value) < _VOLUME_K_THRESHOLD:
        return "count" if abs(value) >= 100 else "small"
    if 1 <= abs(value) < 100:
        return "aov"
    return "small"


def approximate_number(value: float | int | str, *, unit: str = "", kind: NumberKind | None = None) -> str:
    """Format a single numeric value for human-readable conclusion briefs."""
    if isinstance(value, str):
        text = value.strip()
        if not text or _ALREADY_FORMATTED.search(text):
            return text
        try:
            numeric = float(text.replace(",", ""))
        except ValueError:
            return text
    else:
        numeric = float(value)

    resolved_kind = kind or infer_number_kind(value=numeric, unit=unit)

    if resolved_kind == "identifier":
        if float(numeric).is_integer():
            return str(int(numeric))
        return str(numeric)

    if resolved_kind == "volume":
        thousands = numeric / 1_000
        rounded = round(thousands)
        if rounded == 0 and numeric != 0:
            rounded = 1 if numeric > 0 else -1
        return f"{rounded}k"

    if resolved_kind == "share":
        pct = numeric * 100 if abs(numeric) <= 1 else numeric
        return f"{round(pct)}%"

    if resolved_kind == "mom_pct":
        pct = numeric * 100 if abs(numeric) <= 1 else numeric
        rounded = round(pct, 1)
        if rounded == int(rounded):
            return f"{int(rounded)}%"
        return f"{rounded}%"

    if resolved_kind == "aov":
        rounded = round(numeric, 1)
        if rounded == int(rounded):
            return str(int(rounded))
        return f"{rounded:.1f}"

    if resolved_kind == "count":
        return str(int(round(numeric)))

    # small
    if abs(numeric) >= 100:
        return str(int(round(numeric)))
    rounded = round(numeric, 1)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.1f}"


def _approximate_token(match: re.Match[str]) -> str:
    token = match.group(1)
    if _ALREADY_FORMATTED.search(token):
        return token
    try:
        numeric = float(token)
    except ValueError:
        return token
    return approximate_number(numeric)


def approximate_text_numbers(text: str) -> str:
    """Replace raw numeric tokens in free-form brief text."""
    if not text:
        return text
    return _NUMBER_TOKEN.sub(_approximate_token, text)


def number_approximation_rules_summary() -> str:
    """Human-readable summary of approximation rules for prompts and docs."""
    return "\n".join(
        [
            "结论简报数字近似规则：",
            "1. 订单量、GMV 等绝对量 ≥1,000：四舍五入到整千，写作 Nk（如 53674 → 54k，657292 → 657k）。",
            "2. 占比/份额（0–1 小数或 unit=share/pct）：转为整数百分比（如 0.3904 → 39%）。",
            "3. MoM/环比等小幅度变化（|值|<0.3 且为小数）：转为带 1 位小数的百分比（如 -0.0746 → -7.5%）。",
            "4. AOV/客单价（unit=usd/order）：保留 1 位小数，整数值不写小数（如 11.77 → 11.8，12.0 → 12）。",
            "5. 行数/计数（unit=rows 或 100–999 的整数）：取整（如 505 → 505）。",
            "6. 标识符（shop_id 等，或 ≥1 亿的大整数）：保持原值不变。",
            "7. 小于 1,000 的普通数值：取整；必要时有 1 位小数（如 3.83 → 3.8）。",
        ]
    )
