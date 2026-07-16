"""Tests for output grain policy helpers."""

from __future__ import annotations

from catemate.core.output_policy import (
    default_time_range_text,
    enabled_module_ids,
    map_daily_performance_intent,
    normalize_time_range_text,
    sanitize_output_grains,
    sanitize_presentation,
    validate_output_grain,
)
from catemate.understanding.generator import _normalize_understood


def test_enabled_module_ids_match_policy() -> None:
    assert set(enabled_module_ids()) == {"monthly_market_trend", "top_sku_info"}


def test_normalize_time_range_rewrites_daily_wording() -> None:
    result = normalize_time_range_text("默认优先使用近30天或最新可用周期")
    assert result == default_time_range_text()
    assert "近30天" not in result


def test_map_daily_performance_to_market_trend() -> None:
    intents = map_daily_performance_intent(
        ["daily_performance", "top_listing"],
        original_request="看看最近的销量",
    )
    assert intents == ["market_trend", "top_listing"]


def test_map_daily_performance_kept_when_explicit() -> None:
    intents = map_daily_performance_intent(
        ["daily_performance"],
        original_request="我要日度监控近30天",
    )
    assert intents == ["daily_performance"]


def test_sanitize_output_grains_replaces_date() -> None:
    assert sanitize_output_grains(["grass_region", "grass_date"]) == [
        "grass_region",
        "grass_month",
    ]


def test_sanitize_presentation_daily_table() -> None:
    assert sanitize_presentation("daily_table") == "trend_table"


def test_validate_output_grain_detects_forbidden() -> None:
    assert validate_output_grain(["grass_date", "grass_region"]) == ["grass_date"]


def test_normalize_understood_applies_policy() -> None:
    understood = _normalize_understood(
        {
            "analysis_intents": ["daily_performance"],
            "time_range": "近30天销量",
        },
        original_request="最近的销量",
    )
    assert understood["analysis_intents"] == ["market_trend"]
    assert "近30天" not in understood["time_range"]
