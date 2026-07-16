"""Tests for blueprint catalog validation."""

from __future__ import annotations

from catemate.orchestration.blueprint_validator import validate_blueprint_against_catalog
from catemate.orchestration.schemas import BlueprintSection, ExpectedShape, ReportBlueprint

_SAMPLE_CATALOG = [
    {
        "module_id": "monthly_market_trend",
        "allowed_grains": ["category", "shop", "item"],
        "allowed_metrics": ["gmv", "orders", "aov"],
    },
    {
        "module_id": "top_sku_info",
        "allowed_grains": ["item"],
        "allowed_metrics": ["orders", "gmv"],
    },
]


def _valid_blueprint() -> ReportBlueprint:
    return ReportBlueprint(
        goal="测试目标",
        sections=[
            BlueprintSection(
                section_id="s_market_trend",
                title="市场趋势",
                sub_question="GMV 趋势如何？",
                module_id="monthly_market_trend",
                metric_id="gmv",
                grain="category",
                expected_shape=ExpectedShape(
                    grain=["grass_region", "grass_month"],
                    metrics=["gmv"],
                    presentation="trend_table",
                ),
            )
        ],
    )


def test_valid_blueprint_passes() -> None:
    valid, errors = validate_blueprint_against_catalog(_valid_blueprint(), _SAMPLE_CATALOG)
    assert valid is True
    assert errors == []


def test_unknown_module_rejected() -> None:
    blueprint = _valid_blueprint()
    blueprint.sections[0].module_id = "nonexistent_module"
    valid, errors = validate_blueprint_against_catalog(blueprint, _SAMPLE_CATALOG)
    assert valid is False
    assert any("unknown module_id" in error for error in errors)


def test_invalid_metric_rejected() -> None:
    blueprint = _valid_blueprint()
    blueprint.sections[0].metric_id = "clicks"
    valid, errors = validate_blueprint_against_catalog(blueprint, _SAMPLE_CATALOG)
    assert valid is False
    assert any("allowed_metrics" in error for error in errors)


def test_invalid_grain_rejected() -> None:
    blueprint = ReportBlueprint(
        goal="测试",
        sections=[
            BlueprintSection(
                section_id="s_top_sku",
                title="Top SKU",
                sub_question="头部 SKU？",
                module_id="top_sku_info",
                metric_id="orders",
                grain="category",
                expected_shape=ExpectedShape(metrics=["orders"]),
            )
        ],
    )
    valid, errors = validate_blueprint_against_catalog(blueprint, _SAMPLE_CATALOG)
    assert valid is False
    assert any("allowed_grains" in error for error in errors)


def test_duplicate_section_id_rejected() -> None:
    section = _valid_blueprint().sections[0]
    blueprint = ReportBlueprint(goal="x", sections=[section, section.model_copy()])
    valid, errors = validate_blueprint_against_catalog(blueprint, _SAMPLE_CATALOG)
    assert valid is False
    assert any("duplicate section_id" in error for error in errors)


def test_empty_sections_rejected() -> None:
    valid, errors = validate_blueprint_against_catalog(
        ReportBlueprint(goal="x", sections=[]),
        _SAMPLE_CATALOG,
    )
    assert valid is False
    assert any("at least one section" in error for error in errors)


def test_forbidden_module_rejected() -> None:
    blueprint = ReportBlueprint(
        goal="测试",
        sections=[
            BlueprintSection(
                section_id="s_daily",
                title="日度",
                sub_question="日度如何？",
                module_id="daily_cncb_performance",
                metric_id="orders",
                grain="category",
                expected_shape=ExpectedShape(metrics=["orders"]),
            )
        ],
    )
    valid, errors = validate_blueprint_against_catalog(blueprint, _SAMPLE_CATALOG)
    assert valid is False
    assert any("unknown module_id" in error or "forbidden" in error for error in errors)


def test_forbidden_presentation_rejected() -> None:
    blueprint = _valid_blueprint()
    blueprint.sections[0].expected_shape.presentation = "daily_table"
    valid, errors = validate_blueprint_against_catalog(blueprint, _SAMPLE_CATALOG)
    assert valid is False
    assert any("presentation" in error and "forbidden" in error for error in errors)


def test_forbidden_output_grain_rejected() -> None:
    blueprint = _valid_blueprint()
    blueprint.sections[0].expected_shape.grain = ["grass_region", "grass_date"]
    valid, errors = validate_blueprint_against_catalog(blueprint, _SAMPLE_CATALOG)
    assert valid is False
    assert any("expected_shape.grain" in error for error in errors)


def test_daily_wording_in_title_rejected() -> None:
    blueprint = _valid_blueprint()
    blueprint.sections[0].title = "新加坡近期日度销量"
    valid, errors = validate_blueprint_against_catalog(blueprint, _SAMPLE_CATALOG)
    assert valid is False
    assert any("daily output" in error for error in errors)
