"""V2 solve loop pipeline continuation."""

from __future__ import annotations

import json
from pathlib import Path

from catemate.ai.client import CateMateAIClient
from catemate.execution.runner import execute_analysis_plan
from catemate.modules.data_workbook import write_data_workbook
from catemate.orchestration.derived_tables import is_comparison_table_id
from catemate.orchestration.solve_loop import run_solve_loop, save_solve_loop_state
from catemate.pipeline.manifest import (
    PipelineManifest,
    load_pipeline_manifest,
    register_subset_scope_artifacts,
    update_and_save_manifest,
)
from catemate.pipeline.runner import PipelineRunResult
from catemate.understanding.clarification import save_understanding_spec, user_declined_rawdata
from catemate.understanding.schemas import (
    ClarifyingQuestion,
    QuestionCategory,
    QuestionType,
    RequirementUnderstandingSpec,
)
from catemate.understanding.solve_loop_readiness import ensure_understanding_ready_for_solve_loop


def continue_v2_solve_loop(
    *,
    manifest_path: Path,
    manifest: PipelineManifest,
    understanding_spec: RequirementUnderstandingSpec,
    understanding_spec_path: Path,
    output_dir: Path,
    safe_case_id: str,
    stamp: str,
    processed_data_dir: Path,
    user_declined_data: bool = False,
    ai_client: CateMateAIClient | None = None,
) -> PipelineRunResult:
    understanding_spec = ensure_understanding_ready_for_solve_loop(understanding_spec, ai_client=ai_client)
    save_understanding_spec(understanding_spec, understanding_spec_path)

    declined = user_declined_data or user_declined_rawdata(understanding_spec)
    loop_result = None
    state = None
    loop_error: Exception | None = None

    try:
        loop_result = run_solve_loop(
            understanding_spec,
            user_declined_data=declined,
            processed_data_dir=processed_data_dir,
            run_output_dir=output_dir,
            ai_client=ai_client,
        )
        state = loop_result.state
    except Exception as exc:
        loop_error = exc
    finally:
        metadata = state.metadata if state is not None else None
        register_subset_scope_artifacts(
            manifest_path,
            output_dir,
            state_metadata=metadata,
        )

    if loop_error is not None:
        if state is not None:
            solve_loop_state_path = output_dir / f"solve_loop_state_{safe_case_id}_{stamp}.json"
            save_solve_loop_state(state, solve_loop_state_path)
            update_and_save_manifest(
                manifest_path=manifest_path,
                case_id=manifest.case_id,
                timestamp=stamp,
                request_text=manifest.request_text,
                provider=manifest.provider,
                model=manifest.model,
                planning_mode="v2_solve_loop",
                case_config_path=Path(manifest.case_config_path) if manifest.case_config_path else None,
                understanding_spec_path=understanding_spec_path,
                solve_loop_state_path=solve_loop_state_path,
                status="failed",
                error_step="solve_loop",
                error_message=str(loop_error),
            )
        else:
            update_and_save_manifest(
                manifest_path=manifest_path,
                case_id=manifest.case_id,
                timestamp=stamp,
                request_text=manifest.request_text,
                provider=manifest.provider,
                model=manifest.model,
                planning_mode="v2_solve_loop",
                case_config_path=Path(manifest.case_config_path) if manifest.case_config_path else None,
                understanding_spec_path=understanding_spec_path,
                status="failed",
                error_step="solve_loop",
                error_message=str(loop_error),
            )
        failed_manifest = load_pipeline_manifest(manifest_path)
        return PipelineRunResult(
            exit_code=1,
            manifest_path=manifest_path,
            manifest=failed_manifest,
            error_message=str(loop_error),
        )

    assert loop_result is not None and state is not None

    solve_loop_state_path = output_dir / f"solve_loop_state_{safe_case_id}_{stamp}.json"
    save_solve_loop_state(state, solve_loop_state_path)

    if state.rawdata_questions and state.phase == "data_clarification":
        _sync_rawdata_questions_to_understanding(understanding_spec, understanding_spec_path, state)

    blueprint_path = None
    analysis_plan_path = None
    verdict_path = None
    data_workbook_path = None

    if state.blueprint is not None:
        blueprint_path = output_dir / f"report_blueprint_{safe_case_id}_{stamp}.json"
        blueprint_path.write_text(
            json.dumps(state.blueprint.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if state.plan is not None:
        analysis_plan_path = output_dir / f"analysis_plan_{safe_case_id}_{stamp}.json"
        analysis_plan_path.write_text(
            json.dumps(state.plan.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if state.verdict is not None:
        verdict_path = output_dir / f"solve_verdict_{safe_case_id}_{stamp}.json"
        verdict_path.write_text(
            json.dumps(state.verdict.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    status = "awaiting_rawdata_clarification"
    if state.phase == "done" and state.plan is not None:
        execution = loop_result.execution
        if execution is None:
            execution = execute_analysis_plan(
                state.plan,
                processed_data_dir=processed_data_dir,
                scope_cache=loop_result.scope_cache,
            )
        data_workbook_path = output_dir / f"data_workbook_{safe_case_id}_{stamp}.xlsx"
        write_data_workbook(state=state, execution=execution, output_path=data_workbook_path)
        status = "data_workbook_generated"
    elif state.phase == "data_clarification" and declined:
        status = "awaiting_rawdata_clarification"

    subset_paths = _subset_paths_from_metadata(state.metadata, output_dir)

    updated = update_and_save_manifest(
        manifest_path=manifest_path,
        case_id=manifest.case_id,
        timestamp=stamp,
        request_text=manifest.request_text,
        provider=manifest.provider,
        model=manifest.model,
        planning_mode="v2_solve_loop",
        case_config_path=Path(manifest.case_config_path) if manifest.case_config_path else None,
        understanding_spec_path=understanding_spec_path,
        report_blueprint_path=blueprint_path,
        analysis_plan_path=analysis_plan_path,
        solve_loop_state_path=solve_loop_state_path,
        solve_verdict_path=verdict_path,
        data_workbook_path=data_workbook_path,
        subset_scope_dir=subset_paths.get("subset_scope_dir"),
        sub_l3_filter_spec_path=subset_paths.get("sub_l3_filter_spec_path"),
        sub_l3_filter_rules_path=subset_paths.get("sub_l3_filter_rules_path"),
        status=status,
    )
    return PipelineRunResult(exit_code=0, manifest_path=manifest_path, manifest=updated)


def _subset_paths_from_metadata(metadata: dict, output_dir: Path) -> dict[str, Path | None]:
    subset_scope_dir = metadata.get("subset_scope_dir")
    filter_spec = metadata.get("sub_l3_filter_spec_path")
    filter_rules = metadata.get("sub_l3_filter_rules_path")
    return {
        "subset_scope_dir": Path(subset_scope_dir) if subset_scope_dir else None,
        "sub_l3_filter_spec_path": Path(filter_spec) if filter_spec else None,
        "sub_l3_filter_rules_path": Path(filter_rules) if filter_rules else None,
    }


def _sync_rawdata_questions_to_understanding(
    spec: RequirementUnderstandingSpec,
    spec_path: Path,
    state,
) -> None:
    existing_ids = {q.question_id for q in spec.clarifying_questions}
    extra: list[ClarifyingQuestion] = []
    for item in state.rawdata_questions:
        if item.question_id in existing_ids:
            continue
        if is_comparison_table_id(item.table_id):
            continue
        is_plan_config = item.clarification_kind == "plan_config"
        extra.append(
            ClarifyingQuestion(
                question_id=item.question_id,
                question=item.question,
                reason=item.reason,
                expected_answer_type=(
                    QuestionType.FREE_TEXT if is_plan_config else QuestionType.FILE_PATH
                ),
                question_category=QuestionCategory.RAWDATA,
                rawdata_grain="" if is_plan_config else item.grain,
                rawdata_table_id="" if is_plan_config else item.table_id,
                clarification_kind=item.clarification_kind,
            )
        )
    if not extra:
        return
    updated = spec.model_copy(update={"clarifying_questions": list(spec.clarifying_questions) + extra})
    spec_path.write_text(
        json.dumps(updated.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
