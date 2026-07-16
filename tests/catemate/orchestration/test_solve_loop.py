"""Tests for solve loop orchestration."""

from __future__ import annotations

from catemate.orchestration.blueprint_generator import build_report_blueprint
from catemate.orchestration.plan_composer import compose_analysis_plan
from catemate.orchestration.solve_loop import run_solve_loop
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


def test_blueprint_has_sections() -> None:
    blueprint = build_report_blueprint(_sample_spec())
    assert blueprint.sections
    assert blueprint.sections[0].section_id


def test_compose_plan_runs() -> None:
    spec = _sample_spec()
    blueprint = build_report_blueprint(spec)
    plan = compose_analysis_plan(blueprint, spec)
    assert plan.runs
    assert plan.runs[0].module_id == "monthly_market_trend"


def test_solve_loop_single_iteration() -> None:
    state = run_solve_loop(_sample_spec(), max_iterations=1)
    assert state.blueprint is not None
    assert state.plan is not None
