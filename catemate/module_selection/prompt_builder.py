"""Build prompts for Module Selection Layer."""

from __future__ import annotations

import json
from typing import Any

from catemate.understanding.schemas import RequirementUnderstandingSpec


SYSTEM_PROMPT = """你是 CateMate 的 data module 选择 agent。

你的任务：基于 RequirementUnderstandingSpec 和全部 active data modules，输出 ModuleSelectionPlan JSON。

硬性规则：
1. 只做 module selection，不生成 RequirementPlanningSpec，不生成 workbook。
2. 必须遍历所有提供的 active modules，每个 module 恰好一条 module_decision。
3. 每个 module 必须有 decision：selected / optional / rejected / needs_confirmation。
4. selected 必须说明为什么选；rejected 必须说明为什么不选。
5. selected / optional / needs_confirmation 应优先继承 module.default_charts 中与需求匹配的 chart_intent。
6. 不要凭空发明 chart_intent；若必须新增，rule_source=system_inferred 且写 override_reason（v1 应极少）。
7. 不确定但可能有用的模块标 optional；需要确认但不阻塞标 needs_confirmation。
8. 默认推进：可合理推断则 selected/optional，不要轻易全部 rejected。

匹配指引（结合 understanding.analysis_intents）：
- market_trend：通常优先 rm_monthly_category_performance；用户明确 DECK/看板/近12个月/过去数据 → 可选 dashboard_history_market_trend
- 两个趋势模块重复时：选一个 selected，另一个 optional/rejected，reason 说明口径/时间窗口差异
- daily_performance / CNCB / 渗透 / 广告 / 活动 / LPP / CFS → dashboard_daily_cncb_performance
- price_tier → dashboard_price_tier_distribution（价格段需求必须优先）
- top_listing / 平均价格样本价 / price_reference → dashboard_top_listing
- keywords → dashboard_keywords
- top_shop / 头部卖家 / 店铺排名 → dashboard_top_shop

输出中文 reason / matched_user_need；枚举字段使用英文规定值。
"""


def build_module_selection_messages(
    understanding_spec: RequirementUnderstandingSpec,
    module_summaries: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build chat messages for module selection."""
    understanding_payload = understanding_spec.model_dump(mode="json")
    user_payload = {
        "task": "基于 RequirementUnderstandingSpec 为每个 active module 输出 module_decision，组成 ModuleSelectionPlan。",
        "requirement_understanding_spec": understanding_payload,
        "active_data_modules": module_summaries,
        "required_json_shape": {
            "spec_version": "module_selection_v1",
            "case_id": understanding_spec.case_id,
            "status": "ready",
            "understanding_summary": "简短摘要",
            "module_decisions": [
                {
                    "module_id": "必须覆盖每个 active module",
                    "module_name": "",
                    "decision": "selected|optional|rejected|needs_confirmation",
                    "confidence": "high|medium|low",
                    "matched_intents": ["market_trend"],
                    "matched_user_need": "匹配的用户需求描述",
                    "reason": "选择或拒绝理由",
                    "source_tables": ["table_id"],
                    "selected_chart_intents": [
                        {
                            "chart_intent": "来自 module.default_charts",
                            "chart_title": "title_template",
                            "chart_type": "trend|bar|share|table|bubble",
                            "source_default_chart": "chart_intent",
                            "x_axis": "字段名或 null",
                            "y_axis": ["字段名"],
                            "series": "字段名或 null",
                            "dimensions": ["字段名"],
                            "sort_rule": "",
                            "top_n": None,
                            "rule_source": "module_default",
                            "override_reason": "",
                        }
                    ],
                    "assumptions": [],
                    "confirmation_questions": [],
                }
            ],
            "global_assumptions": [],
            "global_warnings": [],
        },
        "output_constraints": [
            "module_decisions 数量必须等于 active_data_modules 数量",
            "每个 module_id 恰好出现一次",
            "rejected 模块不需要 selected_chart_intents",
            "只输出 JSON 对象",
        ],
    }

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "请根据以下上下文输出 ModuleSelectionPlan JSON（使用 module_decisions 数组）。\n"
                + json.dumps(user_payload, ensure_ascii=False, indent=2)
            ),
        },
    ]
