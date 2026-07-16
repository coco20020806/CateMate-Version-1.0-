"""Prompt builders for blueprint and verify steps."""

from __future__ import annotations

import json
from typing import Any

from catemate.core.output_policy import time_range_guidance_text
from catemate.orchestration.schemas import BlueprintSection, ExpectedShape, ReportBlueprint
from catemate.understanding.schemas import RequirementUnderstandingSpec

BLUEPRINT_SYSTEM_PROMPT = """你是 CateMate 的报告蓝图设计师。

任务：基于 module_catalog 中已有的数据模块能力，想象一份能回答用户需求的类目分析报告，
输出 ReportBlueprint JSON。

硬性规则：
1. 只输出合法 JSON 对象，根结构为 {"goal": "...", "sections": [...]}。
2. 不要输出 Markdown、代码块或解释性前后缀。
3. 每节必须指定 module_id、metric_id、grain，且三者必须来自 module_catalog 的 allowed 值。
4. module_catalog 仅包含当前 status=active 的 V2 module；不得使用 catalog 外的 module_id。
5. section_id 使用 snake_case，建议前缀 s_（如 s_market_trend）；可复用常见 ID 或生成语义化新 ID。
6. 每节只回答一个可验证子问题；章节数量建议 2–6 节。
7. 遵循 analysis_playbook 的推荐顺序，但跳过与需求无关的章节。
8. 禁止选择 module 的 not_suitable_for / avoid_when 所描述的场景。
9. expected_shape.presentation 仅限：trend_table | ranked_table | share_table | table
10. expected_shape.grain 须为月度粒度（如 grass_month）；不得输出日度粒度。
11. expected_shape.metrics 必须包含该节的 metric_id。
12. 用户说「最近」「近期」时，用 monthly_market_trend 的最新可用月份，不要规划日度章节。
13. Sub-L3 或 related concept pack 场景应包含 top_sku_info 类章节。
14. time_range 解释规则见 payload 中的 output_grain_policy。
"""


def build_blueprint_messages(
    understanding: RequirementUnderstandingSpec,
    *,
    module_catalog: list[dict[str, Any]],
    analysis_playbook: str,
) -> list[dict[str, str]]:
    payload = {
        "task": "生成 ReportBlueprint",
        "analysis_playbook": analysis_playbook,
        "output_grain_policy": time_range_guidance_text(),
        "requirement": _requirement_payload(understanding),
        "module_catalog": module_catalog,
        "output_schema": _output_schema_example(),
    }
    return [
        {"role": "system", "content": BLUEPRINT_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]


def build_blueprint_prompt(
    understanding: RequirementUnderstandingSpec,
    module_catalog_summary: str,
) -> str:
    """Legacy string prompt; prefer build_blueprint_messages."""
    messages = build_blueprint_messages(
        understanding,
        module_catalog=[{"summary": module_catalog_summary}],
        analysis_playbook="",
    )
    return messages[1]["content"]


def build_verify_prompt(goal: str, section_summaries: str, table_summaries: str) -> str:
    return (
        f"分析目标: {goal}\n"
        f"报告章节:\n{section_summaries}\n"
        f"已生成数据表:\n{table_summaries}\n"
        "判断这些表是否足以回答各子问题。返回 solved / partial / retry。"
    )


def _requirement_payload(understanding: RequirementUnderstandingSpec) -> dict[str, Any]:
    understood = understanding.understood
    return {
        "original_request": understanding.original_request,
        "conversation_summary": understanding.conversation_summary,
        "understood": understood.model_dump(mode="json"),
        "user_answers": [item.model_dump(mode="json") for item in understanding.user_answers],
        "assumptions": [item.model_dump(mode="json") for item in understanding.assumptions],
    }


def _output_schema_example() -> dict[str, Any]:
    example = ReportBlueprint(
        goal="报告总目标",
        sections=[
            BlueprintSection(
                section_id="s_market_trend",
                title="市场整体趋势",
                sub_question="某类目在各站点的月度 GMV 趋势如何？",
                module_id="monthly_market_trend",
                metric_id="gmv",
                grain="category",
                expected_shape=ExpectedShape(
                    grain=["grass_region", "grass_month"],
                    metrics=["gmv"],
                    presentation="trend_table",
                ),
            )
        ],
    )
    return example.model_dump(mode="json")
