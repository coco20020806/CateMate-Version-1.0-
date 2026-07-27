"""Tests for v2_runner subset artifact registration on solve loop failure."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from catemate.orchestration.schemas import SolveLoopState
from catemate.orchestration.solve_loop import SolveLoopRunResult
from catemate.pipeline.manifest import load_pipeline_manifest, update_and_save_manifest
from catemate.pipeline.runner import PipelineRunResult
from catemate.pipeline.v2_runner import continue_v2_solve_loop
from catemate.scope.scope_cache import MANIFEST_FILENAME
from catemate.scope.sub_l3_artifacts import FILTER_RULES_MD_FILENAME, FILTER_SPEC_FILENAME
from catemate.understanding.schemas import RequirementUnderstandingSpec


def _minimal_manifest(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "pipeline_manifest_test_20260717.json"
    update_and_save_manifest(
        manifest_path=manifest_path,
        case_id="test",
        timestamp="20260717",
        request_text="智能喂食器",
        provider="test",
        model="test",
        planning_mode="v2_solve_loop",
        case_config_path=tmp_path / "case.yaml",
        understanding_spec_path=tmp_path / "understanding.json",
        status="category_confirmed",
    )
    return manifest_path


def _write_understanding(path: Path) -> None:
    spec = RequirementUnderstandingSpec.model_validate(
        {
            "status": "ready_for_module_selection",
            "original_request": "智能喂食器",
            "understood": {
                "target_category_text": "智能喂食器",
                "sub_l3_concept": {"is_sub_l3": True, "display_name": "智能喂食器", "parent_l3": "Bowls & Feeders"},
                "related_concept_pack": {
                    "concept_id": "smart_pet_feeder",
                    "display_name": "智能喂食器",
                    "parent_l3": "Bowls & Feeders",
                    "scope_note": "test",
                    "smart_signals": ["smart"],
                    "pet_context": ["pet"],
                    "boost_terms": [],
                    "exclude_terms": [],
                    "min_score": 0.55,
                },
            },
            "readiness": {"can_select_modules": True},
        }
    )
    path.write_text(json.dumps(spec.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_subset_scope(output_dir: Path) -> None:
    subset_dir = output_dir / "subset_scope"
    subset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = subset_dir / "sub_l3_items__Pets__Pet_Accessories__Bowls_Feeders__VN.csv"
    pd.DataFrame({"item_name": ["smart feeder"], "orders": [1]}).to_csv(csv_path, index=False)
    (subset_dir / FILTER_SPEC_FILENAME).write_text("{}", encoding="utf-8")
    (subset_dir / FILTER_RULES_MD_FILENAME).write_text("# rules", encoding="utf-8")
    (subset_dir / MANIFEST_FILENAME).write_text(
        json.dumps({"entries": [{"csv_file": csv_path.name, "output_rows": 1}]}),
        encoding="utf-8",
    )


def test_continue_v2_registers_subset_scope_when_solve_loop_fails(tmp_path: Path) -> None:
    manifest_path = _minimal_manifest(tmp_path)
    understanding_path = tmp_path / "understanding.json"
    _write_understanding(understanding_path)
    _write_subset_scope(tmp_path)

    with patch("catemate.pipeline.v2_runner.ensure_understanding_ready_for_solve_loop", side_effect=lambda spec, **_: spec):
        with patch("catemate.pipeline.v2_runner.run_solve_loop", side_effect=RuntimeError("boom")):
            with patch("catemate.pipeline.v2_runner.save_understanding_spec"):
                result = continue_v2_solve_loop(
                    manifest_path=manifest_path,
                    manifest=load_pipeline_manifest(manifest_path),
                    understanding_spec=RequirementUnderstandingSpec.model_validate(
                        json.loads(understanding_path.read_text(encoding="utf-8"))
                    ),
                    understanding_spec_path=understanding_path,
                    output_dir=tmp_path,
                    safe_case_id="test",
                    stamp="20260717",
                    processed_data_dir=tmp_path,
                )

    assert isinstance(result, PipelineRunResult)
    assert result.exit_code == 1
    manifest = load_pipeline_manifest(manifest_path)
    assert manifest.subset_scope_dir
    assert "subset_scope" in manifest.subset_scope_dir
