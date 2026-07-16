"""Tests for rawdata clarification skip and solve loop continuation."""

from __future__ import annotations

from catemate.orchestration.solve_loop import run_solve_loop
from catemate.understanding.clarification import (
    SKIPPED_ANSWER,
    is_clarification_complete,
    user_declined_rawdata,
)
from catemate.understanding.schemas import (
    AnalysisIntent,
    ClarifyingQuestion,
    QuestionCategory,
    QuestionType,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    UnderstoodRequirement,
    UnderstandingStatus,
    UserAnswer,
)


def _spec_with_skipped_rawdata() -> RequirementUnderstandingSpec:
    return RequirementUnderstandingSpec(
        case_id="test",
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="VN pet GMV trend + top shop",
        understood=UnderstoodRequirement(
            target_sites=["VN"],
            target_category_text="Pet",
            analysis_intents=[AnalysisIntent.MARKET_TREND, AnalysisIntent.TOP_SHOP],
        ),
        clarifying_questions=[
            ClarifyingQuestion(
                question_id="rawdata_shop_shop_monthly_sales",
                question="Provide shop_monthly_sales path or skip",
                reason="missing shop table",
                expected_answer_type=QuestionType.FILE_PATH,
                question_category=QuestionCategory.RAWDATA,
                rawdata_grain="shop",
                rawdata_table_id="shop_monthly_sales",
            )
        ],
        user_answers=[
            UserAnswer(
                question_id="rawdata_shop_shop_monthly_sales",
                answer=SKIPPED_ANSWER,
                answered_at="2026-07-15T08:00:00+00:00",
            )
        ],
        readiness=RequirementReadiness(can_select_modules=True),
    )


def test_user_declined_rawdata_when_skipped() -> None:
    spec = _spec_with_skipped_rawdata()
    assert user_declined_rawdata(spec)
    assert is_clarification_complete(spec)


def test_solve_loop_exits_data_clarification_when_rawdata_skipped() -> None:
    spec = _spec_with_skipped_rawdata()
    state = run_solve_loop(spec, max_iterations=1, user_declined_data=user_declined_rawdata(spec))
    assert state.phase == "done"
    assert state.verdict is not None
    assert state.verdict.verdict in {"partial", "solved"}
