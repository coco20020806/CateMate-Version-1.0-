"""V2 solve loop pipeline continuation."""

from __future__ import annotations

import json
from pathlib import Path

from catemate.ai.client import CateMateAIClient
from catemate.execution.runner import execute_analysis_plan
from catemate.modules.data_workbook import write_data_workbook
from catemate.orchestration.solve_loop import run_solve_loop, save_solve_loop_state
from catemate.pipeline.manifest import PipelineManifest, update_and_save_manifest
from catemate.pipeline.runner import PipelineRunResult
from catemate.understanding.clarification import user_declined_rawdata
from catemate.understanding.schemas import (
    ClarifyingQuestion,
    QuestionCategory,
    QuestionType,
    RequirementUnderstandingSpec,
)


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
    declined = user_declined_data or user_declined_rawdata(understanding_spec)
    state = run_solve_loop(
        understanding_spec,
        user_declined_data=declined,
        processed_data_dir=processed_data_dir,
        ai_client=ai_client,
    )

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
        execution = execute_analysis_plan(state.plan, processed_data_dir=processed_data_dir)
        data_workbook_path = output_dir / f"data_workbook_{safe_case_id}_{stamp}.xlsx"
        write_data_workbook(state=state, execution=execution, output_path=data_workbook_path)
        status = "data_workbook_generated"
    elif state.phase == "data_clarification" and declined:
        # User skipped rawdata but loop still waiting — should not happen after fix.
        status = "awaiting_rawdata_clarification"

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
        status=status,
    )
    return PipelineRunResult(exit_code=0, manifest_path=manifest_path, manifest=updated)


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
        extra.append(
            ClarifyingQuestion(
                question_id=item.question_id,
                question=item.question,
                reason=item.reason,
                expected_answer_type=QuestionType.FILE_PATH,
                question_category=QuestionCategory.RAWDATA,
                rawdata_grain=item.grain,
                rawdata_table_id=item.table_id,
            )
        )
    if not extra:
        return
    updated = spec.model_copy(update={"clarifying_questions": list(spec.clarifying_questions) + extra})
    spec_path.write_text(
        json.dumps(updated.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

