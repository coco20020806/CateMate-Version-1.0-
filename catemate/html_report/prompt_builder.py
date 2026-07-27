"""Prompt builder for visual report LLM proposal."""

from __future__ import annotations

import json
from typing import Any

from catemate.html_report.schemas import VisualReportSpec

VISUAL_REPORT_SYSTEM_PROMPT = """你是 CateMate 的数据可视化编排顾问。

任务：基于用户问题、报告蓝图、workbook_digest 与规则绑定草案 rule_bindings，
输出 VisualReportSpec JSON，用于后续 Plotly HTML 报告渲染。

硬性规则：
1. 只输出合法 JSON 对象，根结构必须符合 output_schema，不要 Markdown 或解释性前后缀。
2. chart_type 仅限：trend | bar | share | table | kpi_row。
3. 每个 binding 的 x_field / y_fields / series_field 必须存在于对应 table 的 columns（见 table_columns）。
4. 不得编造 table_id 或字段名；不得新增 digest 中不存在的表。
5. 优先保留 rule_bindings 中高 confidence 的绑定；仅对 low/medium 项调整 chart_type、title、role、visible。
6. narrative 优先使用 conclusion_brief 中同 section_id 的 direct_answer；若无则根据 digest 写 1-3 句。
7. executive_summary 写 2-4 句，概括报告核心发现（可引用 digest 数字，但不编造）。
8. unsolved section（见 unsolved_section_ids）默认 charts.visible=false，status=unsolved，并在 data_gaps 说明。
9. 同 section 多表：primary 一张主图，其余 role=secondary。
10. spec_status 固定为 draft。
"""


def _output_schema_example() -> dict[str, Any]:
    return VisualReportSpec.model_validate(
        {
            "case_id": "demo_case",
            "original_question": "用户原始问题",
            "report_goal": "报告目标",
            "executive_summary": "2-4 句执行摘要",
            "sections": [
                {
                    "section_id": "s_orders_trend",
                    "title": "订单月度趋势",
                    "sub_question": "各站点订单趋势如何？",
                    "narrative": "BR 最新订单 54k，呈连续下滑。",
                    "status": "solved",
                    "charts": [
                        {
                            "chart_id": "s_orders_trend_orders_by_site_month",
                            "section_id": "s_orders_trend",
                            "table_id": "orders_by_site_month",
                            "module_id": "monthly_market_trend",
                            "chart_type": "trend",
                            "title": "各站点订单月度趋势",
                            "x_field": "grass_month",
                            "y_fields": ["orders"],
                            "series_field": "grass_region",
                            "visible": True,
                            "role": "primary",
                            "binding_source": "chart_preset",
                            "confidence": "high",
                            "notes": [],
                        }
                    ],
                }
            ],
            "data_gaps": [],
            "generated_at": "2026-07-17T00:00:00+00:00",
            "spec_status": "draft",
        }
    ).model_dump(mode="json")


def build_visual_report_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    body = {
        "task": "生成 VisualReportSpec",
        "payload": payload,
        "output_schema": _output_schema_example(),
        "output_constraints": [
            "chart_type 仅限 trend|bar|share|table|kpi_row",
            "字段必须存在于 table_columns",
            "spec_status 必须为 draft",
        ],
    }
    return [
        {"role": "system", "content": VISUAL_REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(body, ensure_ascii=False, indent=2)},
    ]
