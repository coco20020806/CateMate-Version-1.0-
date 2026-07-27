"""Tests for conclusion brief number approximation."""

from __future__ import annotations

from catemate.conclusion_brief.brief_number_approximator import apply_number_approximation
from catemate.conclusion_brief.number_format import (
    approximate_number,
    approximate_text_numbers,
    infer_number_kind,
)
from catemate.conclusion_brief.schemas import ConclusionBrief


def test_infer_number_kind_from_unit() -> None:
    assert infer_number_kind(value=53674.33, unit="orders") == "volume"
    assert infer_number_kind(value=0.39, unit="share") == "share"
    assert infer_number_kind(value=11.77, unit="usd/order") == "aov"
    assert infer_number_kind(value=505, unit="rows") == "count"
    assert infer_number_kind(value=1663734800, unit="shop_id") == "identifier"


def test_approximate_number_volume_share_aov() -> None:
    assert approximate_number(53674.33046953047, unit="orders") == "54k"
    assert approximate_number(657291.7350444624, unit="usd") == "657k"
    assert approximate_number(350499.3434, unit="orders") == "350k"
    assert approximate_number(0.3903704086247126, unit="share") == "39%"
    assert approximate_number(-0.07463707176507994, unit="pct") == "-7.5%"
    assert approximate_number(11.77119459376124, unit="usd/order") == "11.8"
    assert approximate_number(12.24592331743365, unit="usd/order") == "12.2"
    assert approximate_number(505, unit="rows") == "505"
    assert approximate_number(1663734800, unit="shop_id") == "1663734800"
    assert approximate_number(3.833333333333333, unit="orders") == "3.8"


def test_approximate_text_numbers_in_prose() -> None:
    text = (
        "BR 最新订单为 53674.33046953047、GMV 为 657291.7350444624；"
        "占比为 0.3903704086247126，MoM 为 -0.07463707176507994。"
    )
    approx = approximate_text_numbers(text)
    assert "54k" in approx
    assert "657k" in approx
    assert "39%" in approx
    assert "-7.5%" in approx
    assert "53674" not in approx


def test_apply_number_approximation_on_brief() -> None:
    brief = ConclusionBrief.model_validate(
        {
            "original_question": "趋势如何？",
            "report_goal": "看订单",
            "executive_summary": "BR 订单 53674.33046953047，占比 0.3903704086247126。",
            "overall_assessment": {
                "dimension": "growth_potential",
                "verdict": "承压",
                "confidence": "medium",
                "reasoning": "订单从 59224.37619047619 降至 53674.33046953047。",
                "supporting_evidence": [],
            },
            "sections": [
                {
                    "section_id": "s1",
                    "title": "订单",
                    "sub_question": "订单？",
                    "direct_answer": "最新 53674.33046953047 orders。",
                    "key_numbers": [
                        {
                            "label": "BR 订单",
                            "value": "53674.33046953047",
                            "unit": "orders",
                        }
                    ],
                    "qualitative_judgments": [],
                }
            ],
        }
    )
    approx = apply_number_approximation(brief)
    assert "54k" in approx.executive_summary
    assert approx.sections[0].key_numbers[0].value == "54k"
    assert "54k" in approx.overall_assessment.reasoning
