"""Reusable natural-language requirement pipeline runner."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from catemate.ai.client import CateMateAIClient
from catemate.ai.settings import AISettings
from catemate.case_generation.context_loader import (
    ensure_case_id,
    load_category_tree_l3_candidates,
    load_data_module_summaries,
    load_reference_case_summaries,
    load_request_text,
    safe_slug,
    save_case_config_yaml,
)
from catemate.case_generation.confirmation_enrichment import enrich_confirmation_templates
from catemate.case_generation.generator import CaseConfigGenerator
from catemate.config.case_config import load_case_config
from catemate.core.paths import (
    CONFIG_DIR,
    OUTPUTS_DIR,
    PROCESSED_DATA_DIR,
    PROJECT_ROOT,
    RAW_DATA_DIR,
    is_default_outputs_root,
    pipeline_run_dir,
)
from catemate.modules.category_analysis_data_requirement import (
    build_category_analysis_requirement_spec,
    write_category_analysis_requirement_workbook,
)
from catemate.module_selection.schemas import ModuleSelectionPlan
from catemate.module_selection.selector import ModuleSelectionSelector
from catemate.pipeline.manifest import (
    PipelineManifest,
    default_manifest_path,
    load_pipeline_manifest,
    resolve_manifest_path,
    update_and_save_manifest,
)
from catemate.planning.context_loader import build_planning_context
from catemate.planning.module_selection_adapter import build_planning_spec_from_module_selection
from catemate.planning.planner import RequirementPlanner
from catemate.schemas.category_requirement import RequirementContext
from catemate.understanding.clarification import (
    is_clarification_complete,
    normalize_clarifying_question_ids,
    requires_clarification_gate,
    save_understanding_spec,
)
from catemate.understanding.clarification_merge import (
    merge_clarification_answers_into_understanding,
    needs_clarification_merge,
)
from catemate.understanding.generator import RequirementUnderstandingGenerator
from catemate.understanding.schemas import RequirementUnderstandingSpec, UnderstandingStatus

PlanningMode = Literal["ai_direct", "module_selection"]
StopAfter = Literal["case_config", "understanding", "module_selection", "planning"] | None
ContinueAfter = Literal["clarification", "module_selection", "planning"]


@dataclass
class PipelineRunResult:
    exit_code: int
    manifest_path: Path | None = None
    manifest: PipelineManifest | None = None
    error_message: str = ""


def run_pipeline_from_request_text(
    *,
    request_text: str = "",
    request_file: Path | None = None,
    planning_mode: PlanningMode = "module_selection",
    output_dir: Path | str = OUTPUTS_DIR,
    reference_cases_dir: Path | str = CONFIG_DIR / "cases",
    data_modules_dir: Path | str = CONFIG_DIR / "data_modules",
    processed_manifest_path: Path | str = PROCESSED_DATA_DIR / "processed_manifest.yaml",
    raw_data_dir: Path | str = RAW_DATA_DIR,
    processed_data_dir: Path | str = PROCESSED_DATA_DIR,
    category_tree_lookup: Path | str = PROCESSED_DATA_DIR / "sph_category_tree_lookup.csv",
    stop_after: StopAfter = None,
    ai_client: CateMateAIClient | None = None,
    timestamp: str | None = None,
) -> PipelineRunResult:
    """Run the full or partial natural-language pipeline; returns manifest on success or partial failure."""
    output_dir = Path(output_dir)
    stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    use_run_dirs = is_default_outputs_root(output_dir)
    if use_run_dirs:
        output_dir = pipeline_run_dir("generated_case", stamp)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    case_config_path: Path | None = None
    planning_spec_path: Path | None = None
    requirement_workbook_path: Path | None = None
    understanding_spec_path: Path | None = None
    module_selection_plan_path: Path | None = None
    pipeline_manifest_path: Path | None = None
    case_id = ""
    safe_case_id = f"generated_case_{stamp}"
    provider = ""
    model = ""

    pipeline_manifest_path = default_manifest_path(output_dir, safe_case_id, stamp)

    try:
        text = load_request_text(request_text, request_file)
    except Exception as exc:
        return PipelineRunResult(exit_code=2, error_message=str(exc))

    try:
        reference_cases = load_reference_case_summaries(Path(reference_cases_dir))
        load_data_module_summaries(Path(data_modules_dir))
    except Exception as exc:
        return PipelineRunResult(exit_code=2, error_message=str(exc))

    if ai_client is None:
        try:
            settings = AISettings.from_env()
            provider = settings.provider
            model = settings.model
            ai_client = CateMateAIClient(settings)
        except ValueError as exc:
            return PipelineRunResult(exit_code=2, error_message=str(exc))
    else:
        provider = getattr(ai_client, "provider", "") or ""
        model = getattr(ai_client, "model", "") or ""

    client = ai_client

    try:
        case_config = CaseConfigGenerator(client).generate(
            request_text=text,
            reference_case_configs=reference_cases,
            data_module_summaries=load_data_module_summaries(Path(data_modules_dir)),
        )
        case_config = ensure_case_id(case_config, timestamp=stamp)
        case_id = case_config.case_id
        safe_case_id = safe_slug(case_config.case_id, timestamp=stamp)
        if use_run_dirs:
            output_dir = pipeline_run_dir(case_id, stamp)
            output_dir.mkdir(parents=True, exist_ok=True)
        case_config_path = output_dir / f"generated_case_config_{safe_case_id}_{stamp}.yaml"
        save_case_config_yaml(case_config, case_config_path)
        pipeline_manifest_path = default_manifest_path(output_dir, safe_case_id, stamp)
        manifest = update_and_save_manifest(
            manifest_path=pipeline_manifest_path,
            case_id=case_id,
            timestamp=stamp,
            request_text=text,
            provider=provider,
            model=model,
            planning_mode=planning_mode,
            case_config_path=case_config_path,
            status="case_config_generated",
        )
    except Exception as exc:
        update_and_save_manifest(
            manifest_path=pipeline_manifest_path,
            case_id=case_id,
            timestamp=stamp,
            request_text=text,
            provider=provider,
            model=model,
            planning_mode=planning_mode,
            status="failed",
            error_step="case_config",
            error_message=str(exc),
        )
        return PipelineRunResult(
            exit_code=1,
            manifest_path=pipeline_manifest_path,
            error_message=str(exc),
        )

    if stop_after == "case_config":
        return PipelineRunResult(exit_code=0, manifest_path=pipeline_manifest_path, manifest=manifest)

    if planning_mode == "ai_direct":
        try:
            planning_spec = _run_ai_direct_planning(
                client=client,
                case_config_path=case_config_path,
                manifest_path=Path(processed_manifest_path),
                data_modules_dir=Path(data_modules_dir),
            )
            planning_spec_path = output_dir / f"planning_spec_{safe_case_id}_{stamp}.json"
            planning_spec_path.write_text(
                json.dumps(planning_spec.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            manifest = update_and_save_manifest(
                manifest_path=pipeline_manifest_path,
                case_id=case_id,
                timestamp=stamp,
                request_text=text,
                provider=provider,
                model=model,
                planning_mode=planning_mode,
                case_config_path=case_config_path,
                planning_spec_path=planning_spec_path,
                status="planning_generated",
            )
        except Exception as exc:
            _write_failed_manifest(
                pipeline_manifest_path=pipeline_manifest_path,
                case_id=case_id,
                timestamp=stamp,
                request_text=text,
                provider=provider,
                model=model,
                planning_mode=planning_mode,
                case_config_path=case_config_path,
                error_step="planning",
                error_message=str(exc),
            )
            return PipelineRunResult(exit_code=1, manifest_path=pipeline_manifest_path, error_message=str(exc))
    else:
        try:
            understanding_spec = _run_understanding(
                client=client,
                request_text=text,
                data_modules_dir=Path(data_modules_dir),
                category_tree_lookup_path=Path(category_tree_lookup),
            )
            understanding_spec = normalize_clarifying_question_ids(understanding_spec)
            understanding_spec_path = output_dir / f"requirement_understanding_{safe_case_id}_{stamp}.json"
            understanding_spec_path.write_text(
                json.dumps(understanding_spec.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            manifest = update_and_save_manifest(
                manifest_path=pipeline_manifest_path,
                case_id=case_id,
                timestamp=stamp,
                request_text=text,
                provider=provider,
                model=model,
                planning_mode=planning_mode,
                case_config_path=case_config_path,
                understanding_spec_path=understanding_spec_path,
                status="understanding_generated",
            )
        except Exception as exc:
            _write_failed_manifest(
                pipeline_manifest_path=pipeline_manifest_path,
                case_id=case_id,
                timestamp=stamp,
                request_text=text,
                provider=provider,
                model=model,
                planning_mode=planning_mode,
                case_config_path=case_config_path,
                understanding_spec_path=None,
                error_step="understanding",
                error_message=str(exc),
            )
            return PipelineRunResult(exit_code=1, manifest_path=pipeline_manifest_path, error_message=str(exc))

        if stop_after == "understanding":
            return PipelineRunResult(exit_code=0, manifest_path=pipeline_manifest_path, manifest=manifest)

        if understanding_spec.status != UnderstandingStatus.READY_FOR_MODULE_SELECTION:
            blocked_reason = "; ".join(understanding_spec.readiness.blocking_reasons) or str(
                understanding_spec.status.value
            )
            manifest = update_and_save_manifest(
                manifest_path=pipeline_manifest_path,
                case_id=case_id,
                timestamp=stamp,
                request_text=text,
                provider=provider,
                model=model,
                planning_mode=planning_mode,
                case_config_path=case_config_path,
                understanding_spec_path=understanding_spec_path,
                status="blocked_by_understanding",
                error_step="understanding",
                error_message=blocked_reason,
            )
            return PipelineRunResult(
                exit_code=1,
                manifest_path=pipeline_manifest_path,
                manifest=manifest,
                error_message=blocked_reason,
            )

        if requires_clarification_gate(understanding_spec) and not is_clarification_complete(
            understanding_spec
        ):
            manifest = update_and_save_manifest(
                manifest_path=pipeline_manifest_path,
                case_id=case_id,
                timestamp=stamp,
                request_text=text,
                provider=provider,
                model=model,
                planning_mode=planning_mode,
                case_config_path=case_config_path,
                understanding_spec_path=understanding_spec_path,
                status="awaiting_clarification",
            )
            return PipelineRunResult(exit_code=0, manifest_path=pipeline_manifest_path, manifest=manifest)

        return _continue_after_understanding(
            client=client,
            manifest_path=pipeline_manifest_path,
            manifest=manifest,
            case_id=case_id,
            safe_case_id=safe_case_id,
            stamp=stamp,
            request_text=text,
            provider=provider,
            model=model,
            case_config_path=case_config_path,
            understanding_spec=understanding_spec,
            understanding_spec_path=understanding_spec_path,
            output_dir=output_dir,
            data_modules_dir=Path(data_modules_dir),
            raw_data_dir=Path(raw_data_dir),
            processed_data_dir=Path(processed_data_dir),
            stop_after=stop_after,
        )

    if stop_after == "planning":
        return PipelineRunResult(exit_code=0, manifest_path=pipeline_manifest_path, manifest=manifest)

    try:
        loaded_case = enrich_confirmation_templates(load_case_config(case_config_path))
        requirement_context = RequirementContext(
            original_request=loaded_case.original_request,
            target_category_text=loaded_case.target_category_text,
            business_background=loaded_case.business_background,
            delivery_audience=loaded_case.delivery_audience,
            delivery_format=loaded_case.delivery_format,
            target_sites=loaded_case.target_sites,
            time_range=loaded_case.time_range,
        )
        requirement_spec = build_category_analysis_requirement_spec(
            context=requirement_context,
            raw_data_dir=Path(raw_data_dir),
            processed_data_dir=Path(processed_data_dir),
            case_config=loaded_case,
            planning_spec=planning_spec,
        )
        requirement_workbook_path = (
            output_dir / f"category_analysis_data_requirement_from_planning_{safe_case_id}_{stamp}.xlsx"
        )
        write_category_analysis_requirement_workbook(requirement_spec, requirement_workbook_path)
        manifest = update_and_save_manifest(
            manifest_path=pipeline_manifest_path,
            case_id=case_id,
            timestamp=stamp,
            request_text=text,
            provider=provider,
            model=model,
            planning_mode=planning_mode,
            case_config_path=case_config_path,
            understanding_spec_path=understanding_spec_path,
            module_selection_plan_path=module_selection_plan_path,
            planning_spec_path=planning_spec_path,
            requirement_workbook_path=requirement_workbook_path,
            status="workbook_generated",
        )
    except Exception as exc:
        _write_failed_manifest(
            pipeline_manifest_path=pipeline_manifest_path,
            case_id=case_id,
            timestamp=stamp,
            request_text=text,
            provider=provider,
            model=model,
            planning_mode=planning_mode,
            case_config_path=case_config_path,
            understanding_spec_path=understanding_spec_path,
            module_selection_plan_path=module_selection_plan_path,
            planning_spec_path=planning_spec_path,
            error_step="workbook",
            error_message=str(exc),
        )
        return PipelineRunResult(exit_code=1, manifest_path=pipeline_manifest_path, error_message=str(exc))

    return PipelineRunResult(exit_code=0, manifest_path=pipeline_manifest_path, manifest=manifest)


def run_pipeline_continue_from_manifest(
    manifest_path: Path,
    *,
    start_after: ContinueAfter = "clarification",
    data_modules_dir: Path | str = CONFIG_DIR / "data_modules",
    raw_data_dir: Path | str = RAW_DATA_DIR,
    processed_data_dir: Path | str = PROCESSED_DATA_DIR,
    stop_after: StopAfter = None,
    ai_client: CateMateAIClient | None = None,
) -> PipelineRunResult:
    """Resume a paused pipeline from manifest (after clarification or mid-run)."""
    manifest_path = Path(manifest_path)
    try:
        manifest = load_pipeline_manifest(manifest_path)
    except Exception as exc:
        return PipelineRunResult(exit_code=2, error_message=str(exc))

    if manifest.planning_mode != "module_selection":
        return PipelineRunResult(
            exit_code=2,
            error_message="continue-from-manifest only supports planning_mode=module_selection.",
        )

    if manifest.status == "workbook_generated":
        return PipelineRunResult(exit_code=0, manifest_path=manifest_path, manifest=manifest)

    case_config_path = resolve_manifest_path(PROJECT_ROOT, manifest.case_config_path)
    understanding_spec_path = resolve_manifest_path(PROJECT_ROOT, manifest.understanding_spec_path)
    if case_config_path is None or understanding_spec_path is None:
        return PipelineRunResult(exit_code=2, error_message="Manifest missing case_config or understanding_spec path.")

    try:
        understanding_spec = _load_understanding_spec(understanding_spec_path)
    except Exception as exc:
        return PipelineRunResult(exit_code=2, error_message=str(exc))

    if not is_clarification_complete(understanding_spec):
        return PipelineRunResult(
            exit_code=1,
            manifest_path=manifest_path,
            manifest=manifest,
            error_message="Clarifying questions are not all answered or skipped.",
        )

    if ai_client is None:
        try:
            settings = AISettings.from_env()
            provider = settings.provider
            model = settings.model
            ai_client = CateMateAIClient(settings)
        except ValueError as exc:
            return PipelineRunResult(exit_code=2, error_message=str(exc))
    else:
        provider = getattr(ai_client, "provider", "") or manifest.provider
        model = getattr(ai_client, "model", "") or manifest.model

    if start_after == "clarification" and needs_clarification_merge(understanding_spec):
        try:
            understanding_spec = merge_clarification_answers_into_understanding(
                understanding_spec,
                ai_client,
                data_module_summaries=load_data_module_summaries(Path(data_modules_dir)),
            )
            save_understanding_spec(understanding_spec, understanding_spec_path)
            manifest = update_and_save_manifest(
                manifest_path=manifest_path,
                case_id=manifest.case_id,
                timestamp=manifest.timestamp,
                request_text=manifest.request_text,
                provider=provider,
                model=model,
                planning_mode=manifest.planning_mode,
                case_config_path=case_config_path,
                understanding_spec_path=understanding_spec_path,
                status="clarification_completed",
            )
        except Exception as exc:
            return PipelineRunResult(
                exit_code=1,
                manifest_path=manifest_path,
                manifest=manifest,
                error_message=f"Failed to merge clarification answers: {exc}",
            )

    safe_case_id = safe_slug(manifest.case_id, timestamp=manifest.timestamp)
    output_dir = manifest_path.parent

    return _continue_after_understanding(
        client=ai_client,
        manifest_path=manifest_path,
        manifest=manifest,
        case_id=manifest.case_id,
        safe_case_id=safe_case_id,
        stamp=manifest.timestamp,
        request_text=manifest.request_text,
        provider=provider,
        model=model,
        case_config_path=case_config_path,
        understanding_spec=understanding_spec,
        understanding_spec_path=understanding_spec_path,
        output_dir=output_dir,
        data_modules_dir=Path(data_modules_dir),
        raw_data_dir=Path(raw_data_dir),
        processed_data_dir=Path(processed_data_dir),
        stop_after=stop_after,
        start_after=start_after,
        existing_module_selection_plan_path=resolve_manifest_path(
            PROJECT_ROOT, manifest.module_selection_plan_path
        ),
        existing_planning_spec_path=resolve_manifest_path(PROJECT_ROOT, manifest.planning_spec_path),
    )


def _load_understanding_spec(path: Path) -> RequirementUnderstandingSpec:
    payload = json.loads(path.read_text(encoding="utf-8"))
    spec = RequirementUnderstandingSpec.model_validate(payload)
    return normalize_clarifying_question_ids(spec)


def _continue_after_understanding(
    *,
    client: CateMateAIClient,
    manifest_path: Path,
    manifest: PipelineManifest,
    case_id: str,
    safe_case_id: str,
    stamp: str,
    request_text: str,
    provider: str,
    model: str,
    case_config_path: Path,
    understanding_spec: RequirementUnderstandingSpec,
    understanding_spec_path: Path,
    output_dir: Path,
    data_modules_dir: Path,
    raw_data_dir: Path,
    processed_data_dir: Path,
    stop_after: StopAfter = None,
    start_after: ContinueAfter = "clarification",
    existing_module_selection_plan_path: Path | None = None,
    existing_planning_spec_path: Path | None = None,
) -> PipelineRunResult:
    module_selection_plan_path = existing_module_selection_plan_path
    module_plan: ModuleSelectionPlan | None = None
    planning_spec_path = existing_planning_spec_path
    planning_spec = None

    if start_after == "clarification" or (
        start_after == "module_selection" and module_selection_plan_path is None
    ):
        try:
            module_plan = _run_module_selection(
                client=client,
                understanding_spec=understanding_spec,
                understanding_spec_path=understanding_spec_path,
                data_modules_dir=data_modules_dir,
            )
            module_selection_plan_path = output_dir / f"module_selection_{safe_case_id}_{stamp}.json"
            module_selection_plan_path.write_text(
                json.dumps(module_plan.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            manifest = update_and_save_manifest(
                manifest_path=manifest_path,
                case_id=case_id,
                timestamp=stamp,
                request_text=request_text,
                provider=provider,
                model=model,
                planning_mode="module_selection",
                case_config_path=case_config_path,
                understanding_spec_path=understanding_spec_path,
                module_selection_plan_path=module_selection_plan_path,
                status="module_selection_generated",
            )
        except Exception as exc:
            _write_failed_manifest(
                pipeline_manifest_path=manifest_path,
                case_id=case_id,
                timestamp=stamp,
                request_text=request_text,
                provider=provider,
                model=model,
                planning_mode="module_selection",
                case_config_path=case_config_path,
                understanding_spec_path=understanding_spec_path,
                error_step="module_selection",
                error_message=str(exc),
            )
            return PipelineRunResult(exit_code=1, manifest_path=manifest_path, error_message=str(exc))

        if stop_after == "module_selection":
            return PipelineRunResult(exit_code=0, manifest_path=manifest_path, manifest=manifest)
    elif module_selection_plan_path and module_selection_plan_path.exists():
        module_plan = ModuleSelectionPlan.model_validate(
            json.loads(module_selection_plan_path.read_text(encoding="utf-8"))
        )
    else:
        return PipelineRunResult(
            exit_code=2,
            manifest_path=manifest_path,
            error_message="Module selection plan missing; cannot continue from planning.",
        )

    if start_after in {"clarification", "module_selection"} or (
        start_after == "planning" and planning_spec_path is None
    ):
        try:
            planning_spec = build_planning_spec_from_module_selection(
                understanding_spec=understanding_spec,
                module_selection_plan=module_plan,
            )
            planning_spec_path = output_dir / f"planning_spec_from_module_selection_{safe_case_id}_{stamp}.json"
            planning_spec_path.write_text(
                json.dumps(planning_spec.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            manifest = update_and_save_manifest(
                manifest_path=manifest_path,
                case_id=case_id,
                timestamp=stamp,
                request_text=request_text,
                provider=provider,
                model=model,
                planning_mode="module_selection",
                case_config_path=case_config_path,
                understanding_spec_path=understanding_spec_path,
                module_selection_plan_path=module_selection_plan_path,
                planning_spec_path=planning_spec_path,
                status="planning_generated",
            )
        except Exception as exc:
            _write_failed_manifest(
                pipeline_manifest_path=manifest_path,
                case_id=case_id,
                timestamp=stamp,
                request_text=request_text,
                provider=provider,
                model=model,
                planning_mode="module_selection",
                case_config_path=case_config_path,
                understanding_spec_path=understanding_spec_path,
                module_selection_plan_path=module_selection_plan_path,
                error_step="planning",
                error_message=str(exc),
            )
            return PipelineRunResult(exit_code=1, manifest_path=manifest_path, error_message=str(exc))

        if stop_after == "planning":
            return PipelineRunResult(exit_code=0, manifest_path=manifest_path, manifest=manifest)
    elif planning_spec_path and planning_spec_path.exists():
        from catemate.planning.schemas import RequirementPlanningSpec

        planning_spec = RequirementPlanningSpec.model_validate(
            json.loads(planning_spec_path.read_text(encoding="utf-8"))
        )
    else:
        return PipelineRunResult(
            exit_code=2,
            manifest_path=manifest_path,
            error_message="Planning spec missing; cannot generate workbook.",
        )

    try:
        loaded_case = enrich_confirmation_templates(load_case_config(case_config_path))
        requirement_context = RequirementContext(
            original_request=loaded_case.original_request,
            target_category_text=loaded_case.target_category_text,
            business_background=loaded_case.business_background,
            delivery_audience=loaded_case.delivery_audience,
            delivery_format=loaded_case.delivery_format,
            target_sites=loaded_case.target_sites,
            time_range=loaded_case.time_range,
        )
        requirement_spec = build_category_analysis_requirement_spec(
            context=requirement_context,
            raw_data_dir=raw_data_dir,
            processed_data_dir=processed_data_dir,
            case_config=loaded_case,
            planning_spec=planning_spec,
        )
        requirement_workbook_path = (
            output_dir / f"category_analysis_data_requirement_from_planning_{safe_case_id}_{stamp}.xlsx"
        )
        write_category_analysis_requirement_workbook(requirement_spec, requirement_workbook_path)
        manifest = update_and_save_manifest(
            manifest_path=manifest_path,
            case_id=case_id,
            timestamp=stamp,
            request_text=request_text,
            provider=provider,
            model=model,
            planning_mode="module_selection",
            case_config_path=case_config_path,
            understanding_spec_path=understanding_spec_path,
            module_selection_plan_path=module_selection_plan_path,
            planning_spec_path=planning_spec_path,
            requirement_workbook_path=requirement_workbook_path,
            status="workbook_generated",
        )
    except Exception as exc:
        _write_failed_manifest(
            pipeline_manifest_path=manifest_path,
            case_id=case_id,
            timestamp=stamp,
            request_text=request_text,
            provider=provider,
            model=model,
            planning_mode="module_selection",
            case_config_path=case_config_path,
            understanding_spec_path=understanding_spec_path,
            module_selection_plan_path=module_selection_plan_path,
            planning_spec_path=planning_spec_path,
            error_step="workbook",
            error_message=str(exc),
        )
        return PipelineRunResult(exit_code=1, manifest_path=manifest_path, error_message=str(exc))

    return PipelineRunResult(exit_code=0, manifest_path=manifest_path, manifest=manifest)


def _run_ai_direct_planning(
    *,
    client: CateMateAIClient,
    case_config_path: Path,
    manifest_path: Path,
    data_modules_dir: Path,
):
    context = build_planning_context(
        case_config_path=case_config_path,
        manifest_path=manifest_path,
        data_modules_dir=data_modules_dir,
    )
    return RequirementPlanner(client).plan(context)


def _run_understanding(
    *,
    client: CateMateAIClient,
    request_text: str,
    data_modules_dir: Path,
    category_tree_lookup_path: Path,
) -> RequirementUnderstandingSpec:
    module_summaries = load_data_module_summaries(data_modules_dir)
    category_tree_candidates = load_category_tree_l3_candidates(category_tree_lookup_path)
    return RequirementUnderstandingGenerator(client).generate(
        request_text=request_text,
        data_module_summaries=module_summaries,
        category_tree_candidates=category_tree_candidates,
    )


def _run_module_selection(
    *,
    client: CateMateAIClient,
    understanding_spec: RequirementUnderstandingSpec,
    understanding_spec_path: Path,
    data_modules_dir: Path,
) -> ModuleSelectionPlan:
    return ModuleSelectionSelector(client).select(
        understanding_spec,
        data_modules_dir=data_modules_dir,
        understanding_spec_path=understanding_spec_path,
    )


def _write_failed_manifest(
    *,
    pipeline_manifest_path: Path,
    case_id: str,
    timestamp: str,
    request_text: str,
    provider: str,
    model: str,
    planning_mode: str,
    case_config_path: Path | None,
    understanding_spec_path: Path | None = None,
    module_selection_plan_path: Path | None = None,
    planning_spec_path: Path | None = None,
    error_step: str,
    error_message: str,
) -> None:
    update_and_save_manifest(
        manifest_path=pipeline_manifest_path,
        case_id=case_id,
        timestamp=timestamp,
        request_text=request_text,
        provider=provider,
        model=model,
        planning_mode=planning_mode,
        case_config_path=case_config_path,
        understanding_spec_path=understanding_spec_path,
        module_selection_plan_path=module_selection_plan_path,
        planning_spec_path=planning_spec_path,
        status="failed",
        error_step=error_step,
        error_message=error_message,
    )
