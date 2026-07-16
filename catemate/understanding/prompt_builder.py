"""Build prompts for Requirement Understanding Layer."""

from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """你是 CateMate 的需求理解与澄清 agent。

你的任务：把用户自然语言需求转成 RequirementUnderstandingSpec JSON。

硬性规则：
1. 只做需求理解，不选择 data module，不生成 RequirementPlanningSpec，不生成 workbook。
2. 必须输出合法 JSON 对象，符合 RequirementUnderstandingSpec 字段结构。
3. 不要输出 Markdown、代码块或解释性前后缀。
4. 字段中的枚举值必须使用英文规定值（如 status、analysis_intents、confidence）。
5. 面向用户的中文说明写在 content、question、description、conversation_summary 等字符串字段中。
6. target_sites 规则：仅当用户明确提到站点/国家/市场（如 VN、越南、SG）时才填写对应站点代码；
   若用户未指定站点，target_sites 必须为 []，表示分析全部站点，禁止默认猜测为 VN 或其他单一站点。

产品原则（默认推进，谨慎追问）：
1. 只要需求大体与类目分析、市场分析、商品/卖家/关键词/价格段等相关，就应积极理解并揣测。
2. 用户通常不会给非常详细的目标；你要像成熟分析师一样主动判断 analysis_intents、站点、类目方向。
3. clarifying_questions 要少而关键（通常 0–3 条）。每条都必须有稳定唯一的 question_id（如 clarify_1）。
4. 列出的每个 clarifying_questions 都会要求用户逐条「自然语言回答」或「跳过」后才能进入 module selection；
   因此不要生成琐碎或可从原文直接推断的问题。
5. 业务细节不清（时间范围、平均价格口径等）优先写入 assumptions；只有确实需要用户拍板时才放入 clarifying_questions。
6. blocks_module_selection 字段可保留但不再作为 gate 依据；澄清 gate 只看 clarifying_questions 是否全部已回答/跳过。
7. 只有两种情况可以阻塞 readiness（非澄清 gate）：
   - out_of_scope：明显与 CateMate 无关（写邮件、写代码、闲聊等）
   - needs_minimum_context：大体相关但完全无法判断分析对象（无类目/商品/关键词/站点/卖家/业务背景任何线索）
8. 用户说「先不要继续」「等我确认」时，可设置 needs_minimum_context 或在 readiness 中说明需等待用户。

Sub-L3 概念识别：
1. 若用户需求比 L3 类目更细（如「智能宠物碗」对应 L3「Bowls & Feeders」），在 understood.sub_l3_concept 中设 is_sub_l3=true。
2. sub_l3_concept.display_name 用用户概念的中文/原文表述；concept_id 用 snake_case 英文。
3. sub_l3_concept.parent_l3 填映射到的 L3 名称。
4. 若 is_sub_l3=true，analysis_intents 应包含 top_listing（表示需要精准子集 SKU 分析）。
5. 普通 L3 类目需求（如「宠物碗」）不要设 is_sub_l3=true。

analysis_intents 可选值：
market_trend, daily_performance, price_tier, top_listing, top_shop, keywords,
category_mapping, site_comparison, price_reference, unknown

data_module_summaries 仅用于理解系统支持哪些分析方向，不要在本层选择具体 module_id。
"""


def build_requirement_understanding_messages(
    request_text: str,
    *,
    data_module_summaries: list[dict] | None = None,
    category_tree_candidates: list[dict[str, str]] | None = None,
    previous_spec: dict | None = None,
    user_answers: list[dict] | None = None,
) -> list[dict[str, str]]:
    """Build chat messages for initial understanding or update."""
    request_text = request_text.strip()
    if not request_text and not previous_spec:
        raise ValueError("request_text is empty and no previous_spec provided.")

    is_update = previous_spec is not None
    task = (
        "根据已有 RequirementUnderstandingSpec 和用户补充回答，更新并输出完整 JSON。"
        if is_update
        else "将自然语言需求转成 RequirementUnderstandingSpec JSON。"
    )

    user_payload: dict[str, Any] = {
        "task": task,
        "request_text": request_text,
        "data_module_summaries": _compact_module_summaries(data_module_summaries or []),
        "category_tree_l3_candidates": category_tree_candidates or [],
        "required_json_shape": {
            "spec_version": "requirement_understanding_v1",
            "case_id": "英文下划线 id，可草稿值",
            "status": "ready_for_module_selection | needs_minimum_context | out_of_scope",
            "original_request": "保留用户原始需求语义",
            "conversation_summary": "你对需求的理解摘要（中文）",
            "understood": {
                "business_background": "",
                "delivery_audience": "待确认",
                "delivery_format": "Excel 或 PPT 等",
                "target_sites": [],
                "target_category_text": "",
                "inferred_category": "",
                "inferred_category_candidates": [
                    {
                        "l1": "",
                        "l2": "",
                        "l3": "",
                        "category_path": "L1 > L2 > L3",
                        "reason": "为何匹配该候选",
                        "confidence": "high|medium|low",
                    }
                ],
                "category_level_hint": "L1/L2/L3/unknown",
                "analysis_intents": ["market_trend"],
                "time_range": "使用源数据可覆盖范围，待确认",
                "output_expectation": "数据需求 workbook / PPT-ready workbook",
                "metric_definitions": {},
                "sub_l3_concept": {
                    "is_sub_l3": False,
                    "concept_id": "",
                    "display_name": "",
                    "parent_l3": "",
                },
            },
            "assumptions": [],
            "uncertainties": [],
            "clarifying_questions": [],
            "user_answers": [],
            "readiness": {
                "can_select_modules": True,
                "blocking_reasons": [],
                "non_blocking_notes": [],
            },
        },
        "output_constraints": [
            "必须返回单个 JSON 对象",
            "默认 status=ready_for_module_selection",
            "非阻塞问题 blocks_module_selection=false",
            "更新时不要丢失 original_request 与已有 assumptions 语义",
            "若提供 category_tree_l3_candidates，必须优先从中匹配类目候选；inferred_category_candidates 里的每个候选都要带 L1/L2/L3。",
            "不要编造不存在于 category_tree_l3_candidates 的 L3。",
            "若 new_user_answers 包含澄清问答，必须把用户回答融入 understood、conversation_summary、assumptions、metric_definitions；不要新增 clarifying_questions。",
            "用户未明确指定站点时，target_sites 必须为 []（表示全部站点），不要默认填写 VN/SG 等。",
            "skipped=true 的条目优先采用 default_assumption；若无 default_assumption 则保留原假设。",
        ],
    }

    if is_update:
        user_payload["previous_spec"] = previous_spec
        user_payload["new_user_answers"] = user_answers or []

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "请根据以下上下文输出 RequirementUnderstandingSpec JSON。\n"
                + json.dumps(user_payload, ensure_ascii=False, indent=2)
            ),
        },
    ]


def _compact_module_summaries(summaries: list[dict]) -> list[dict]:
    """Keep prompt small: module intent hints only, no module selection."""
    compact: list[dict] = []
    for item in summaries:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                "module_id": item.get("module_id", ""),
                "module_name": item.get("module_name", ""),
                "description": item.get("description", ""),
                "typical_questions": (item.get("typical_questions") or item.get("answerable_questions") or [])[:5],
            }
        )
    return compact
