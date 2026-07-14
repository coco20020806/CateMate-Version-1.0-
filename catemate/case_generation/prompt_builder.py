"""Build prompts for natural-language to CategoryAnalysisCaseConfig conversion."""

from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """你是 CateMate 的需求结构化 agent。

你的任务：把用户自然语言类目分析需求，转成 CategoryAnalysisCaseConfig JSON。

硬性规则：
1. 你不能编造确定事实。
2. 不确定信息要写成：\"待确认\"、空列表，或放入 static_confirmation_items 待确认项。
3. 你不要直接生成报告。
4. 你不要直接规划图表数据。
5. 你不要直接写 Excel。
6. 你只输出合法 JSON，不要输出 Markdown。
7. 输出必须符合 CategoryAnalysisCaseConfig 字段结构。

补充要求：
- 用户需求通常不完整。
- 尽量识别：背景目的、交付对象、交付格式、目标站点、目标类目文本、类目关键词、用户明确提出的分析点、可能需要确认事项。
- 如果用户给出关键词（例如：催肥增重、增蛋、催奶），放入 category_keywords。
- 如果用户明确说“最后定位在 pet healthcare”，放入 target_category_text。
- 如果无法确定 L1/L2/L3，不要编造完整类目路径，可写用户原文或待确认。
- 如果用户明确说“越南”，target_sites 应包含 VN。
- delivery_format 默认 Excel。
- delivery_audience 默认 待确认。
- time_range 默认 使用源数据可覆盖范围，待确认。
"""


CASE_CONFIG_FIELD_HINTS = {
    "case_id": "稳定短 id（英文下划线），例如 pet_healthcare_vn；不确定可先给草稿值。",
    "project_name": "项目名称，中文可读。",
    "original_request": "保留用户原始需求核心语义。",
    "target_category_text": "目标类目文本，可是完整路径，也可是待确认文本。",
    "business_background": "业务背景/目的，不确定写待确认。",
    "delivery_audience": "交付对象，默认待确认。",
    "delivery_format": "默认 Excel。",
    "target_sites": "站点列表，例如 [\"VN\"]。",
    "time_range": "默认 使用源数据可覆盖范围，待确认。",
    "category_keywords": "需求中的关键词列表。",
    "analysis_plan": "用户明确提到的分析点，可转成简化分析行。",
    "data_requirements": "如果能确定再填；否则空列表。",
    "preprocess_plan": "如果能确定再填；否则空列表。",
    "chart_requirements": "第一版可仅写用户明确提到的图表/输出需求。",
    "static_confirmation_items": "需人工确认的事项；每项须含 name（短标签）、question（完整确认问题）、可选 suggested_value/reason。",
}


def build_case_config_messages(
    request_text: str,
    reference_case_configs: list[dict[str, Any]] | None = None,
    data_module_summaries: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """Build chat messages for generating CategoryAnalysisCaseConfig JSON."""
    request_text = request_text.strip()
    if not request_text:
        raise ValueError("request_text is empty.")

    user_payload = {
        "task": "将自然语言需求转成 CategoryAnalysisCaseConfig JSON 草稿。",
        "request_text": request_text,
        "field_hints": CASE_CONFIG_FIELD_HINTS,
        "reference_case_configs": reference_case_configs or [],
        "data_module_summaries": data_module_summaries or [],
        "output_constraints": [
            "必须返回单个 JSON 对象",
            "不要输出额外解释文本",
            "不要输出 Markdown 代码块",
            "不要编造不存在的数据源与事实",
        ],
    }

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "请根据以下上下文输出 CategoryAnalysisCaseConfig JSON。\n"
                + json.dumps(user_payload, ensure_ascii=False, indent=2)
            ),
        },
    ]
