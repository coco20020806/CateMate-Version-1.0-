"""Tests for subset scope precompute."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.scope.schemas import ScopedFrame
from catemate.scope.subset_precompute import precompute_subset_scopes
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
        scope_note="test",
        smart_signals=["smart", "feeder"],
        pet_context=["pet"],
        boost_terms=["feeder"],
        exclude_terms=["chicken"],
        min_score=0.55,
    )
    return RequirementUnderstandingSpec(
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


def test_precompute_skips_without_sub_l3() -> None:
    spec = RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="test",
        understood=UnderstoodRequirement(target_category_text="Stationery"),
        readiness=RequirementReadiness(can_select_modules=True),
    )
    result = precompute_subset_scopes(spec)
    assert not result.precomputed
    assert not result.cache.frames


def test_precompute_loads_existing_cache_without_recompute(tmp_path) -> None:
    spec = _smart_feeder_spec()
    frame = ScopedFrame(
        data=pd.DataFrame({"item_name": ["smart feeder"], "orders": [1]}),
        scope_label="cached",
        scope_spec={},
    )

    with patch("catemate.scope.subset_precompute._count_l3_item_rows", return_value=10):
        with patch("catemate.scope.subset_precompute.execute_scope", return_value=frame) as mock_execute:
            first = precompute_subset_scopes(spec, run_output_dir=tmp_path)
            assert first.precomputed
            assert mock_execute.call_count == 1
            assert first.artifact_paths is not None
            assert list((tmp_path / "subset_scope").glob("sub_l3_items__*.csv"))
            assert (tmp_path / "subset_scope" / "sub_l3_filter_spec.json").exists()
            assert (tmp_path / "subset_scope" / "sub_l3_filter_rules.md").exists()
            entry = next(iter(first.cache.entries.values()))
            assert entry.get("csv_file")

    with patch("catemate.scope.subset_precompute.execute_scope") as mock_execute:
        second = precompute_subset_scopes(spec, run_output_dir=tmp_path)
        mock_execute.assert_not_called()
        assert not second.precomputed
        assert second.cache.frames


@pytest.mark.skipif(
    not __import__("catemate.core.paths", fromlist=["PROCESSED_DATA_DIR"]).PROCESSED_DATA_DIR.exists(),
    reason="processed data unavailable",
)
def test_precompute_produces_smaller_subset_than_l3_items() -> None:
    from catemate.core.paths import PROCESSED_DATA_DIR

    spec = _smart_feeder_spec()
    result = precompute_subset_scopes(spec, processed_data_dir=PROCESSED_DATA_DIR)
    assert result.cache.frames
    entry = next(iter(result.cache.entries.values()))
    assert entry["output_rows"] <= entry["input_rows"]
