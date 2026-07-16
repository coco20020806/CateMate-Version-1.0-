"""Tests for LLM + rules blueprint generation."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from catemate.orchestration.blueprint_generator import build_report_blueprint, normalize_llm_payload
from catemate.orchestration.module_catalog_builder import build_module_catalog_for_blueprint
from catemate.understanding.schemas import (
    AnalysisIntent,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    UnderstoodRequirement,
    UnderstandingStatus,
)


def _sample_spec() -> RequirementUnderstandingSpec:
    return RequirementUnderstandingSpec(
        case_id="test",
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="SG Stationery GMV trend",
        understood=UnderstoodRequirement(
            target_sites=["SG"],
            target_category_text="Stationery",
            analysis_intents=[AnalysisIntent.MARKET_TREND],
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def _llm_payload() -> dict[str, Any]:
    return {
        "goal": "SG 文具类目分析",
        "sections": [
            {
                "section_id": "s_market_trend",
                "title": "市场趋势",
                "sub_question": "SG 文具月度 GMV 趋势？",
                "module_id": "monthly_market_trend",
                "metric_id": "gmv",
                "grain": "category",
                "expected_shape": {
                    "grain": ["grass_region", "grass_month"],
                    "metrics": ["gmv"],
                    "presentation": "trend_table",
                },
            }
        ],
    }


def test_rules_path_without_ai_client() -> None:
    metadata: dict[str, Any] = {}
    blueprint = build_report_blueprint(_sample_spec(), metadata=metadata)
    assert blueprint.sections
    assert blueprint.sections[0].module_id == "monthly_market_trend"
    assert metadata["blueprint_source"] == "rules"


def test_llm_path_with_valid_response() -> None:
    ai_client = MagicMock()
    ai_client.complete_json.return_value = _llm_payload()
    metadata: dict[str, Any] = {}
    blueprint = build_report_blueprint(_sample_spec(), ai_client=ai_client, metadata=metadata)
    assert blueprint.goal == "SG 文具类目分析"
    assert blueprint.sections[0].section_id == "s_market_trend"
    assert metadata["blueprint_source"] == "llm"
    ai_client.complete_json.assert_called_once()


def test_llm_invalid_module_falls_back_to_rules() -> None:
    ai_client = MagicMock()
    payload = _llm_payload()
    payload["sections"][0]["module_id"] = "nonexistent_module"
    ai_client.complete_json.return_value = payload
    metadata: dict[str, Any] = {}
    blueprint = build_report_blueprint(_sample_spec(), ai_client=ai_client, metadata=metadata)
    assert metadata["blueprint_source"] == "rules"
    assert blueprint.sections[0].section_id == "s_market_trend"
    assert "blueprint_llm_errors" in metadata


def test_llm_exception_falls_back_to_rules() -> None:
    ai_client = MagicMock()
    ai_client.complete_json.side_effect = RuntimeError("network error")
    metadata: dict[str, Any] = {}
    blueprint = build_report_blueprint(_sample_spec(), ai_client=ai_client, metadata=metadata)
    assert metadata["blueprint_source"] == "rules"
    assert blueprint.sections


def test_normalize_llm_payload_fills_missing_metrics() -> None:
    payload = _llm_payload()
    payload["sections"][0]["expected_shape"] = {"presentation": "trend_table"}
    catalog = [
        {
            "module_id": "monthly_market_trend",
            "allowed_metrics": ["gmv"],
            "output_grains": ["grass_region", "grass_month"],
        }
    ]
    normalized = normalize_llm_payload(payload, loop_iteration=2, catalog=catalog)
    section = normalized["sections"][0]
    assert section["expected_shape"]["metrics"] == ["gmv"]
    assert normalized["loop_iteration"] == 2


def test_module_catalog_has_only_active_modules() -> None:
    catalog = build_module_catalog_for_blueprint(include_manifest=False)
    ids = [entry["module_id"] for entry in catalog]
    assert ids == ["monthly_market_trend", "top_sku_info"]


def test_llm_draft_module_falls_back_to_rules() -> None:
    ai_client = MagicMock()
    payload = _llm_payload()
    payload["sections"][0]["module_id"] = "daily_cncb_performance"
    payload["sections"][0]["metric_id"] = "orders"
    ai_client.complete_json.return_value = payload
    metadata: dict[str, Any] = {}
    blueprint = build_report_blueprint(_sample_spec(), ai_client=ai_client, metadata=metadata)
    assert metadata["blueprint_source"] == "rules"
    assert "blueprint_llm_errors" in metadata


def test_normalize_llm_payload_drops_forbidden_module() -> None:
    payload = {
        "goal": "测试",
        "sections": [
            {
                "section_id": "s_daily",
                "title": "日度",
                "sub_question": "日度？",
                "module_id": "daily_cncb_performance",
                "metric_id": "orders",
                "grain": "category",
                "expected_shape": {
                    "grain": ["grass_region", "date"],
                    "metrics": ["orders"],
                    "presentation": "daily_table",
                },
            },
            _llm_payload()["sections"][0],
        ],
    }
    catalog = build_module_catalog_for_blueprint(include_manifest=False)
    normalized = normalize_llm_payload(payload, loop_iteration=1, catalog=catalog)
    assert len(normalized["sections"]) == 1
    assert normalized["sections"][0]["module_id"] == "monthly_market_trend"
    assert normalized["sections"][0]["expected_shape"]["presentation"] == "trend_table"
    assert "grass_date" not in normalized["sections"][0]["expected_shape"]["grain"]
    assert "date" not in normalized["sections"][0]["expected_shape"]["grain"]
