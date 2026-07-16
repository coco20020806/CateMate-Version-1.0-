"""Tests for target_sites normalization."""

from __future__ import annotations

from catemate.understanding.generator import _normalize_understanding_payload, _validate_spec
from catemate.understanding.site_normalizer import (
    extract_target_sites_from_text,
    normalize_target_sites,
)
from catemate.understanding.schemas import (
    RequirementReadiness,
    RequirementUnderstandingSpec,
    UnderstoodRequirement,
    UnderstandingStatus,
)


def _spec_with_sites(sites: list[str], request: str) -> RequirementUnderstandingSpec:
    return RequirementUnderstandingSpec(
        case_id="test",
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request=request,
        understood=UnderstoodRequirement(target_sites=sites, target_category_text="宠物类目"),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def test_extract_no_site_from_category_only_request() -> None:
    assert extract_target_sites_from_text("宠物类目月度 GMV 趋势") == []


def test_extract_vn_when_explicit() -> None:
    assert extract_target_sites_from_text("VN 宠物类目月度 GMV 趋势") == ["VN"]
    assert extract_target_sites_from_text("分析越南宠物类目趋势") == ["VN"]


def test_normalize_clears_hallucinated_vn() -> None:
    spec = _spec_with_sites(["VN"], "宠物类目月度 GMV 趋势")
    updated = normalize_target_sites(spec)
    assert updated.understood.target_sites == []


def test_normalize_keeps_explicit_site() -> None:
    spec = _spec_with_sites(["VN", "SG"], "VN 和 SG 宠物类目对比")
    updated = normalize_target_sites(spec)
    assert updated.understood.target_sites == ["VN", "SG"]


def test_generator_pipeline_applies_site_normalizer() -> None:
    payload = _normalize_understanding_payload(
        {
            "status": "ready_for_module_selection",
            "understood": {
                "target_sites": ["VN"],
                "target_category_text": "宠物类目",
                "analysis_intents": ["market_trend"],
            },
        },
        original_request="宠物类目月度 GMV 趋势",
    )
    spec = _validate_spec(payload, original_request="宠物类目月度 GMV 趋势")
    spec = normalize_target_sites(spec)
    assert spec.understood.target_sites == []
