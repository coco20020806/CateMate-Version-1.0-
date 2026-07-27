"""Tests for data workbook assembly."""

from __future__ import annotations

from catemate.execution.result_collector import ExecutionResult
from catemate.modules.data_workbook import build_data_workbook_spec
from catemate.orchestration.schemas import (
    AnalysisPlan,
    BlueprintSection,
    ExpectedShape,
    PlanRun,
    ReportBlueprint,
    SolveVerdict,
)


def test_build_data_workbook_spec() -> None:
    blueprint = ReportBlueprint(
        goal="test",
        sections=[
            BlueprintSection(
                section_id="s1",
                title="trend",
                sub_question="q",
                expected_shape=ExpectedShape(metrics=["gmv"]),
            )
        ],
    )
    plan = AnalysisPlan(
        goal="test",
        runs=[
            PlanRun(
                run_id="r1",
                section_id="s1",
                module_id="monthly_market_trend",
                metric_id="gmv",
                grain="item",
                table_id="item_l3_category_csv",
                is_sub_category=True,
                scope_kind="subset",
                status="executable",
            )
        ],
    )
    verdict = SolveVerdict(verdict="solved", solved_sections=["s1"])
    spec = build_data_workbook_spec(
        blueprint=blueprint,
        plan=plan,
        verdict=verdict,
        execution=ExecutionResult(),
    )
    assert len(spec.blueprint_rows) == 1
    assert len(spec.plan_rows) == 1
    assert spec.plan_rows[0].is_sub_category == 1
    assert spec.plan_rows[0].scope_kind == "subset"
    assert spec.plan_rows[0].table_id == "item_l3_category_csv"
    assert spec.verify_rows[0].verdict == "solved"
