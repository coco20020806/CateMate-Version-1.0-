"""Verify V2 solve loop components (offline, no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.orchestration.blueprint_generator import build_report_blueprint
from catemate.orchestration.catalog_checker import check_plan_catalog_readiness
from catemate.orchestration.plan_composer import compose_analysis_plan
from catemate.orchestration.solve_loop import run_solve_loop
from catemate.understanding.schemas import (
    AnalysisIntent,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    UnderstoodRequirement,
    UnderstandingStatus,
)


def main() -> int:
    spec = RequirementUnderstandingSpec(
        case_id="verify_v2",
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="VN Pet Healthcare 月度 GMV 趋势与头部 shop 对比",
        understood=UnderstoodRequirement(
            target_sites=["VN"],
            target_category_text="Pet Healthcare",
            inferred_category="Pet Healthcare",
            analysis_intents=[AnalysisIntent.MARKET_TREND, AnalysisIntent.TOP_SHOP],
        ),
        readiness=RequirementReadiness(can_select_modules=True),
    )

    blueprint = build_report_blueprint(spec)
    plan = compose_analysis_plan(blueprint, spec)
    plan, questions = check_plan_catalog_readiness(plan)

    loop_result = run_solve_loop(spec, max_iterations=1)
    state = loop_result.state

    summary = {
        "blueprint_sections": len(blueprint.sections),
        "plan_runs": len(plan.runs),
        "rawdata_questions": len(questions),
        "solve_phase": state.phase,
        "verdict": state.verdict.verdict if state.verdict else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    assert len(blueprint.sections) >= 1
    assert len(plan.runs) >= 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
