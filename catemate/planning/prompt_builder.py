"""Build chat messages for requirement planning."""

from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """你是 CateMate 的类目分析规划 agent。

硬性规则：
1. 不能编造不存在的数据、表、模块或字段。
2. 只能基于提供的 case config、processed tables、data module configs 做规划。
3. 如果数据不足以支撑某项图表或分析，请写入 missing_data_questions，不要伪造结果。
4. 输出必须是合法 JSON 对象，且符合 RequirementPlanningSpec 字段结构。
5. 不要输出 Markdown、代码块或解释性前后缀，只输出 JSON。
6. chart_type 只能使用：bubble / bar / trend / share / table / unknown。
7. fit_level 只能使用：high / medium / low。
8. target category level 只能使用：L1 / L2 / L3 / unknown。
"""


def build_planning_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    """Create system/user messages for the AI planner."""
    user_payload = {
        "task": "请基于以下上下文，输出 RequirementPlanningSpec JSON。",
        "required_json_fields": {
            "case_id": "字符串，通常来自 case config",
            "project_name": "字符串",
            "interpreted_request": "用中文重述你对需求的理解",
            "target_categories": [
                {
                    "level": "L1/L2/L3/unknown",
                    "path": "类目路径，例如 Pets > Pet Healthcare",
                    "confidence": "0到1之间的数字",
                    "reason": "为什么选择这个类目",
                }
            ],
            "matched_data_modules": [
                {
                    "module_id": "必须来自提供的 data_modules",
                    "module_name": "模块名称",
                    "fit_level": "high/medium/low",
                    "reason": "匹配理由",
                    "required_tables": ["table_id 列表"],
                    "limitations": ["限制"],
                }
            ],
            "proposed_charts": [
                {
                    "chart_id": "稳定 id，例如 trend_by_site",
                    "title": "图表标题",
                    "chart_type": "bubble/bar/trend/share/table/unknown",
                    "data_module_id": "对应模块 id",
                    "table_ids": ["可用 table_id"],
                    "grain": "例如 site x month",
                    "metrics": ["gmv", "orders"],
                    "dimensions": ["site", "month"],
                    "reason": "为什么建议该图",
                }
            ],
            "missing_data_questions": [
                {
                    "question_id": "稳定 id",
                    "question": "需要用户确认或补充的问题",
                    "reason": "为什么需要",
                    "blocks_ppt_ready": True,
                }
            ],
            "assumptions": ["假设列表"],
            "source_notes": ["来源说明列表"],
        },
        "case_config": context.get("case_config", {}),
        "processed_tables": context.get("processed_tables", []),
        "data_modules": context.get("data_modules", []),
        "manifest_meta": context.get("manifest_meta", {}),
    }

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "请阅读以下 JSON 上下文并输出 RequirementPlanningSpec。\n"
                + json.dumps(user_payload, ensure_ascii=False, indent=2)
            ),
        },
    ]
