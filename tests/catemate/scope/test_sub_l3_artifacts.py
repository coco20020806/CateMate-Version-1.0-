"""Tests for Sub-L3 artifact export."""

from __future__ import annotations

import json

import pandas as pd

from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.scope.scope_cache import ScopeCache
from catemate.scope.schemas import ScopedFrame, ScopeSpec
from catemate.scope.sub_l3_artifacts import (
    FILTER_RULES_MD_FILENAME,
    FILTER_SPEC_FILENAME,
    SPEC_VERSION,
    build_filter_spec,
    export_sub_l3_artifacts,
    render_filter_rules_markdown,
)
from catemate.understanding.schemas import (
    InferredCategoryCandidate,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    SubL3Concept,
    UnderstoodRequirement,
    UnderstandingStatus,
)


def _smart_feeder_spec() -> RequirementUnderstandingSpec:
    pack = RelatedConceptPack(
        concept_id="smart_pet_feeder",
        display_name="智能喂食器",
        parent_l3="Bowls & Feeders",
        scope_note="宽定义测试",
        smart_signals=["smart", "feeder"],
        pet_context=["pet"],
        boost_terms=["feeder"],
        exclude_terms=["chicken"],
        min_score=0.55,
    )
    return RequirementUnderstandingSpec(
        case_id="test_case",
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="智能喂食器销量",
        understood=UnderstoodRequirement(
            target_category_text="智能喂食器",
            inferred_category_candidates=[
                InferredCategoryCandidate(
                    l1="Pets",
                    l2="Pet Accessories",
                    l3="Bowls & Feeders",
                    category_path="Pets > Pet Accessories > Bowls & Feeders",
                )
            ],
            sub_l3_concept=SubL3Concept(
                is_sub_l3=True,
                concept_id="smart_pet_feeder",
                display_name="智能喂食器",
                parent_l3="Bowls & Feeders",
            ),
            related_concept_pack=pack,
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )


def _sample_cache() -> ScopeCache:
    cache = ScopeCache()
    frame = ScopedFrame(
        data=pd.DataFrame(
            {
                "item_name": ["smart feeder"],
                "related_score": [0.8],
                "orders": [10],
            }
        ),
        scope_label="VN / Bowls & Feeders / 智能喂食器",
        scope_spec={
            "grain": "item",
            "table_id": "item_l3_category_csv",
            "category_l1": "Pets",
            "category_l2": "Pet Accessories",
            "category_l3": "Bowls & Feeders",
            "target_sites": ["VN"],
        },
        source_id="/raw/item.csv",
    )
    pack = RelatedConceptPack(
        concept_id="smart_pet_feeder",
        display_name="智能喂食器",
        parent_l3="Bowls & Feeders",
        scope_note="宽定义测试",
        smart_signals=["smart"],
        pet_context=["pet"],
        boost_terms=[],
        exclude_terms=[],
        min_score=0.55,
    )
    spec = ScopeSpec(
        grain="item",
        table_id="item_l3_category_csv",
        target_sites=["VN"],
        category_l1="Pets",
        category_l2="Pet Accessories",
        category_l3="Bowls & Feeders",
        related_concept_pack=pack,
        related_min_score=0.55,
    )
    cache.put(spec, frame, input_rows=100)
    return cache


def test_build_filter_spec_structure() -> None:
    spec = _smart_feeder_spec()
    cache = _sample_cache()
    payload = build_filter_spec(spec, cache, case_id="test_case")
    assert payload["spec_version"] == SPEC_VERSION
    assert payload["related_concept_pack"]["concept_id"] == "smart_pet_feeder"
    assert payload["filter_algorithm"]["name"] == "if_related"
    assert payload["data_slices"][0]["csv_file"]


def test_render_filter_rules_markdown_includes_scope_note() -> None:
    spec = _smart_feeder_spec()
    cache = _sample_cache()
    payload = build_filter_spec(spec, cache)
    md = render_filter_rules_markdown(payload)
    assert "宽定义测试" in md
    assert "smart_signals" in md
    assert "智能喂食器" in md


def test_export_sub_l3_artifacts_writes_csv_json_and_md(tmp_path) -> None:
    spec = _smart_feeder_spec()
    cache = _sample_cache()
    paths = export_sub_l3_artifacts(spec, tmp_path, cache)
    assert paths is not None
    assert paths.subset_scope_dir.exists()
    csv_files = list(paths.subset_scope_dir.glob("sub_l3_items__*.csv"))
    assert csv_files
    assert paths.filter_spec_path.exists()
    assert paths.filter_rules_path.exists()
    payload = json.loads(paths.filter_spec_path.read_text(encoding="utf-8"))
    assert payload["spec_version"] == SPEC_VERSION
    assert paths.filter_rules_path.name == FILTER_RULES_MD_FILENAME
    assert paths.filter_spec_path.name == FILTER_SPEC_FILENAME
    manifest = json.loads((paths.subset_scope_dir / "subset_scope_manifest.json").read_text(encoding="utf-8"))
    assert manifest["entries"][0]["csv_file"]
