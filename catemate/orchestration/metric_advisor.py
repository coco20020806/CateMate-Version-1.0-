"""Recommend supplementary metrics for the same blueprint section (Plan A)."""

from __future__ import annotations

import json
import re
from typing import Any

from catemate.ai.client import CateMateAIClient
from catemate.orchestration.module_capability import metric_key
from catemate.orchestration.schemas import (
    AnalysisPlan,
    MetricRecommendation,
    ReportBlueprint,
)
from catemate.understanding.schemas import AnalysisIntent, RequirementUnderstandingSpec

ORDERS_SIGNAL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"销量",
        r"订单",
        r"orders?",
        r"order\s*trend",
        r"volume",
        r"大趋势",
    )
)

GMV_ONLY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"只看\s*gmv",
        r"仅\s*gmv",
        r"only\s*gmv",
        r"gmv\s*only",
        r"不要\s*orders?",
        r"无需\s*orders?",
    )
)


def recommend_supplementary_metrics(
    *,
    understanding: RequirementUnderstandingSpec,
    blueprint: ReportBlueprint,
    plan: AnalysisPlan,
    executed_keys: set[str],
    available_by_run: dict[str, list[str]],
    ai_client: CateMateAIClient | None = None,
) -> list[MetricRecommendation]:
    """Return metrics to add under the same section_id (excluding already executed)."""
    if ai_client is not None:
        try:
            llm_recs = _recommend_with_llm(
                understanding=understanding,
                blueprint=blueprint,
                plan=plan,
                executed_keys=executed_keys,
                available_by_run=available_by_run,
                ai_client=ai_client,
            )
            if llm_recs is not None:
                return llm_recs
        except Exception:
            pass
    return _recommend_with_rules(
        understanding=understanding,
        blueprint=blueprint,
        plan=plan,
        executed_keys=executed_keys,
        available_by_run=available_by_run,
    )


def _recommend_with_rules(
    *,
    understanding: RequirementUnderstandingSpec,
    blueprint: ReportBlueprint,
    plan: AnalysisPlan,
    executed_keys: set[str],
    available_by_run: dict[str, list[str]],
) -> list[MetricRecommendation]:
    text = _combined_text(understanding)
    if _matches_any(text, GMV_ONLY_PATTERNS):
        return []

    intents = {intent.value for intent in understanding.understood.analysis_intents}
    recommendations: list[MetricRecommendation] = []

    for run in plan.runs:
        if run.status != "executable":
            continue
        available = available_by_run.get(run.run_id, [])
        pending = [
            metric
            for metric in available
            if metric_key(run.section_id, metric) not in executed_keys
        ]
        if not pending:
            continue

        primary_key = metric_key(run.section_id, run.metric_id)
        if primary_key not in executed_keys:
            continue

        if "orders" in pending and _should_recommend_orders(understanding, text, intents):
            recommendations.append(
                MetricRecommendation(
                    section_id=run.section_id,
                    metric_id="orders",
                    role="supplementary",
                    reason="市场趋势问题中销量/订单指标可辅助判断规模变化是否由单量驱动",
                    confidence="high",
                )
            )
            pending = [m for m in pending if m != "orders"]

        if "aov" in pending and AnalysisIntent.PRICE_REFERENCE.value in intents:
            recommendations.append(
                MetricRecommendation(
                    section_id=run.section_id,
                    metric_id="aov",
                    role="supplementary",
                    reason="需求涉及价格/客单价参考，补充 aov 指标",
                    confidence="medium",
                )
            )

    return recommendations[:1]


def _should_recommend_orders(
    understanding: RequirementUnderstandingSpec,
    text: str,
    intents: set[str],
) -> bool:
    if AnalysisIntent.MARKET_TREND.value not in intents and "market_trend" not in intents:
        return False
    if _matches_any(text, ORDERS_SIGNAL_PATTERNS):
        return True
    for value in understanding.understood.metric_definitions.values():
        if _matches_any(str(value), ORDERS_SIGNAL_PATTERNS):
            return True
    if understanding.understood.output_expectation and _matches_any(
        understanding.understood.output_expectation, ORDERS_SIGNAL_PATTERNS
    ):
        return True
    return False


def _recommend_with_llm(
    *,
    understanding: RequirementUnderstandingSpec,
    blueprint: ReportBlueprint,
    plan: AnalysisPlan,
    executed_keys: set[str],
    available_by_run: dict[str, list[str]],
    ai_client: CateMateAIClient,
) -> list[MetricRecommendation] | None:
    sections_payload = []
    for run in plan.runs:
        if run.status != "executable":
            continue
        available = available_by_run.get(run.run_id, [])
        pending = [
            metric
            for metric in available
            if metric_key(run.section_id, metric) not in executed_keys
        ]
        if not pending:
            continue
        section = next((s for s in blueprint.sections if s.section_id == run.section_id), None)
        sections_payload.append(
            {
                "section_id": run.section_id,
                "sub_question": section.sub_question if section else "",
                "module_id": run.module_id,
                "executed_metrics": [
                    key.split(":", 1)[1]
                    for key in executed_keys
                    if key.startswith(f"{run.section_id}:")
                ],
                "available_metrics": pending,
            }
        )
    if not sections_payload:
        return []

    payload = {
        "task": "判断是否有辅助指标值得在同一 section 下补跑",
        "original_request": understanding.original_request,
        "metric_definitions": understanding.understood.metric_definitions,
        "analysis_intents": [i.value for i in understanding.understood.analysis_intents],
        "sections": sections_payload,
        "output_schema": {
            "recommendations": [
                {
                    "section_id": "s_market_trend",
                    "metric_id": "orders",
                    "role": "supplementary",
                    "reason": "为何有辅助价值",
                    "confidence": "high|medium|low",
                }
            ]
        },
        "rules": [
            "只推荐 available_metrics 中尚未执行的指标",
            "若辅助指标对回答主问题无明显帮助，返回空 recommendations",
            "市场大趋势类问题通常可用 orders 辅助解释 GMV 变化",
        ],
    }
    messages = [
        {
            "role": "system",
            "content": (
                "你是 CateMate SolveLoop 的指标扩展顾问。"
                "只输出 JSON 对象，字段 recommendations 为数组。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        },
    ]
    response = ai_client.complete_json(messages)
    raw_items = response.get("recommendations") or []
    recommendations: list[MetricRecommendation] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        section_id = str(item.get("section_id") or "").strip()
        metric_id = str(item.get("metric_id") or "").strip()
        if not section_id or not metric_id:
            continue
        key = metric_key(section_id, metric_id)
        if key in executed_keys:
            continue
        run = next((r for r in plan.runs if r.section_id == section_id), None)
        if run is None:
            continue
        available = available_by_run.get(run.run_id, [])
        if metric_id not in available:
            continue
        recommendations.append(
            MetricRecommendation(
                section_id=section_id,
                metric_id=metric_id,
                role="supplementary",
                reason=str(item.get("reason") or ""),
                confidence=str(item.get("confidence") or "medium"),
            )
        )
    return recommendations[:1]


def _combined_text(understanding: RequirementUnderstandingSpec) -> str:
    parts = [
        understanding.original_request,
        understanding.conversation_summary,
        understanding.understood.target_category_text,
        understanding.understood.inferred_category,
        understanding.understood.output_expectation,
        " ".join(understanding.understood.analysis_intents),
    ]
    for value in understanding.understood.metric_definitions.values():
        parts.append(str(value))
    return "\n".join(part for part in parts if part)


def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)
