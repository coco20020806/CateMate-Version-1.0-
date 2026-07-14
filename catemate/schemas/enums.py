"""Shared enum values for CateMate schemas."""

from __future__ import annotations

from enum import StrEnum


class ConfirmationStatus(StrEnum):
    PENDING_CONFIRMATION = "\u5f85\u786e\u8ba4"
    PENDING_SUPPLEMENT = "\u5f85\u8865\u5145"
    SUPPLEMENTED = "\u5df2\u8865\u5145"
    CONFIRMED = "\u5df2\u786e\u8ba4"
    NOT_NEEDED = "\u4e0d\u9700\u8981"
    BLOCKED = "\u963b\u585e"


class ChartType(StrEnum):
    BUBBLE = "bubble"
    BAR = "bar"
    TREND = "trend"
    SHARE = "share"
    TABLE = "table"


class CategoryLevel(StrEnum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    UNKNOWN = "unknown"


class DataSourceStatus(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    PARTIAL = "partial"
    NOT_NEEDED = "not_needed"
    BLOCKED = "blocked"
