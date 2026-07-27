"""Prompt builder for conclusion brief generation."""

from __future__ import annotations

import json
from typing import Any

from catemate.conclusion_brief.number_format import number_approximation_rules_summary
from catemate.conclusion_brief.schemas import ConclusionBrief

CONCLUSION_BRIEF_SYSTEM_PROMPT = """你是 CateMate 的内部品类分析顾问。

任务：基于用户原始问题、报告蓝图（ReportBlueprint）与 workbook_digest 中的真实数据，
输出一份能概括性回答用户问题的结论简报 JSON。

硬性规则：
1. 只输出合法 JSON 对象，根结构必须符合 output_schema，不要 Markdown、代码块或解释性前后缀。
2. 所有数字必须来自 workbook_digest，不得编造；引用时使用近似可读格式（见 number_approximation_rules），不要输出长小数。
3. 每个 qualitative_judgments.reasoning 必须引用至少 1 个 key_numbers.label 或 digest 中的事实。
4. 数据不足时 confidence 降为 low，并在 data_gaps / caveats 中说明。
5. 默认内部使用，不做脱敏；数值按近似规则展示（如 53674 orders → 54k，0.3904 share → 39%）。
6. sections 应尽量与 report_blueprint.sections 对齐（相同 section_id）；每节回答对应 sub_question。
7. overall_assessment 必须直接回应 original_question，给出总体判断（如是否有潜力、是否高增长、是否成熟等）及依据。
8. qualitative_judgments.dimension 建议使用：growth_potential | maturity | market_scale | competitiveness | demand_signal。
9. cross_cutting_insights 提炼跨章节的综合洞察（2-5 条）。
10. 若 solve_verdict 存在未解章节，必须在 data_gaps 中列出。
"""


def _output_schema_example() -> dict[str, Any]:
    return ConclusionBrief.model_validate(
        {
            "original_question": "用户原始问题",
            "report_goal": "报告目标",
            "executive_summary": "2-4 句执行摘要，含关键数字",
            "overall_assessment": {
                "dimension": "growth_potential",
                "verdict": "有潜力",
                "confidence": "medium",
                "reasoning": "依据 ...",
                "supporting_evidence": ["2026-05 SG 月订单量"],
            },
            "sections": [
                {
                    "section_id": "s_market_trend",
                    "title": "章节标题",
                    "sub_question": "子问题",
                    "direct_answer": "直接回答",
                    "key_numbers": [
                        {
                            "label": "2026-05 SG 月订单量",
                            "value": "14661.9",
                            "unit": "orders",
                            "source_table": "orders_by_site_month",
                            "period": "2026-05",
                        }
                    ],
                    "qualitative_judgments": [
                        {
                            "dimension": "growth_potential",
                            "verdict": "温和增长",
                            "confidence": "medium",
                            "reasoning": "最近三期订单 ...",
                            "supporting_evidence": ["2026-05 SG 月订单量"],
                        }
                    ],
                }
            ],
            "cross_cutting_insights": ["综合洞察 1"],
            "data_gaps": [],
            "caveats": [],
            "generated_at": "2026-07-16T00:00:00+00:00",
        }
    ).model_dump(mode="json")


def build_conclusion_brief_messages(digest_payload: dict[str, Any]) -> list[dict[str, str]]:
    payload = {
        "task": "生成结论简报 ConclusionBrief",
        "digest": digest_payload,
        "output_schema": _output_schema_example(),
        "output_constraints": [
            "数字必须来自 workbook_digest.tables",
            "定性结论必须有数据依据",
            "内部使用，不做脱敏",
            "所有展示数字遵循 number_approximation_rules",
        ],
        "number_approximation_rules": number_approximation_rules_summary(),
    }
    return [
        {"role": "system", "content": CONCLUSION_BRIEF_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        },
    ]
