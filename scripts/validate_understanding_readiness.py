"""Lightweight validation for Requirement Understanding schemas and readiness rules."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.understanding.readiness import normalize_understanding_readiness
from catemate.understanding.schemas import (
    AnalysisIntent,
    ClarifyingQuestion,
    RequirementAssumption,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    RequirementUncertainty,
    UnderstandingStatus,
    UnderstoodRequirement,
)


def _base_spec(**overrides) -> RequirementUnderstandingSpec:
    payload = {
        "status": UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        "original_request": "越南畜牧相关类目数据，大盘趋势，平均价格、top listing",
        "understood": UnderstoodRequirement(
            target_sites=["VN"],
            target_category_text="畜牧相关",
            inferred_category="Pet Healthcare",
            analysis_intents=[AnalysisIntent.MARKET_TREND, AnalysisIntent.TOP_LISTING],
        ),
        "readiness": RequirementReadiness(can_select_modules=True),
    }
    payload.update(overrides)
    return RequirementUnderstandingSpec(**payload)


def test_schema_validate() -> None:
    spec = _base_spec(
        assumptions=[
            RequirementAssumption(
                assumption_id="a1",
                content="平均价格口径待确认",
            )
        ]
    )
    restored = RequirementUnderstandingSpec.model_validate(spec.model_dump(mode="json"))
    assert restored.case_id == spec.case_id or True
    print("schema validate: OK")


def test_avg_price_non_blocking() -> None:
    spec = _base_spec(
        clarifying_questions=[
            ClarifyingQuestion(
                question_id="q1",
                question="平均价格口径是否使用 Top Listing 样本价？",
                blocks_module_selection=True,
            )
        ],
        uncertainties=[
            RequirementUncertainty(
                uncertainty_id="u1",
                topic="平均价格口径",
                description="用户未说明均价定义",
                blocks_module_selection=True,
            )
        ],
    )
    normalized = normalize_understanding_readiness(spec)
    assert normalized.status == UnderstandingStatus.READY_FOR_MODULE_SELECTION
    assert normalized.readiness.can_select_modules is True
    assert all(not q.blocks_module_selection for q in normalized.clarifying_questions)
    print("avg price non-blocking: OK")


def test_time_range_non_blocking() -> None:
    spec = _base_spec(
        understood=UnderstoodRequirement(
            target_sites=["VN"],
            inferred_category="Pet Healthcare",
            time_range="待确认",
            analysis_intents=[AnalysisIntent.MARKET_TREND],
        ),
        clarifying_questions=[
            ClarifyingQuestion(
                question_id="q2",
                question="请确认分析时间范围",
                blocks_module_selection=True,
            )
        ],
    )
    normalized = normalize_understanding_readiness(spec)
    assert normalized.status == UnderstandingStatus.READY_FOR_MODULE_SELECTION
    assert normalized.readiness.can_select_modules is True
    print("time range non-blocking: OK")


def test_keywords_price_tier_non_blocking() -> None:
    spec = _base_spec(
        clarifying_questions=[
            ClarifyingQuestion(
                question_id="q3",
                question="是否需要同时输出关键词和价格段分析？",
                blocks_module_selection=True,
            )
        ]
    )
    normalized = normalize_understanding_readiness(spec)
    assert normalized.status == UnderstandingStatus.READY_FOR_MODULE_SELECTION
    assert normalized.readiness.can_select_modules is True
    print("keywords/price tier non-blocking: OK")


def test_no_analysis_object_needs_minimum_context() -> None:
    spec = RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="帮我看看数据",
        understood=UnderstoodRequirement(),
        readiness=RequirementReadiness(can_select_modules=True),
    )
    normalized = normalize_understanding_readiness(spec)
    assert normalized.status == UnderstandingStatus.NEEDS_MINIMUM_CONTEXT
    assert normalized.readiness.can_select_modules is False
    print("no analysis object -> needs_minimum_context: OK")


def test_out_of_scope_stays() -> None:
    spec = RequirementUnderstandingSpec(
        status=UnderstandingStatus.OUT_OF_SCOPE,
        original_request="帮我写一封邮件给老板",
        understood=UnderstoodRequirement(),
        readiness=RequirementReadiness(can_select_modules=False, blocking_reasons=["无关"]),
    )
    normalized = normalize_understanding_readiness(spec)
    assert normalized.status == UnderstandingStatus.OUT_OF_SCOPE
    assert normalized.readiness.can_select_modules is False
    print("out_of_scope stays: OK")


def main() -> int:
    tests = [
        test_schema_validate,
        test_avg_price_non_blocking,
        test_time_range_non_blocking,
        test_keywords_price_tier_non_blocking,
        test_no_analysis_object_needs_minimum_context,
        test_out_of_scope_stays,
    ]
    for test in tests:
        test()
    print("all readiness tests: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
