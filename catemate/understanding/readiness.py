"""Deterministic readiness normalization for requirement understanding specs."""

from __future__ import annotations

import re

from catemate.understanding.schemas import (
    RequirementUnderstandingSpec,
    UnderstandingStatus,
)

# Topics that should never block module selection when only these are unclear.
NON_BLOCKING_TOPIC_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"平均价格|均价|价格口径|样本价格|top\s*listing.*价格",
        r"时间范围|时间窗口|起止|月份|年度",
        r"关键词|价格段|price\s*tier|keyword",
        r"是否要|是否需要|是否包含|要不要",
        r"口径|定义|待确认|不清楚",
        r"类目层级|L1|L2|L3|映射",
        r"站点对比|除.*外.*站点",
    )
)

MARKET_RELEVANCE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"类目|品类|category",
        r"市场|大盘|趋势|GMV|订单|orders",
        r"卖家|店铺|shop|listing|商品",
        r"关键词|keyword",
        r"价格|price|价格段",
        r"站点|site|VN|SG|MY|TH|PH|ID|BR|MX|CL|CO",
        r"collectible|hobby|pet|healthcare|畜牧|手办|盲盒",
        r"CNCB|跨境|渗透",
        r"分析|洞察|insight|数据",
    )
)

OUT_OF_SCOPE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"写一封?邮件",
        r"写代码|编程|python|javascript",
        r"闲聊|讲个笑话",
        r"翻译这段话",
    )
)

WAIT_FOR_USER_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"先不要继续",
        r"等我确认",
        r"暂停",
        r"先别往下",
    )
)

ANALYSIS_OBJECT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"类目|品类|category",
        r"collectible|hobby|pet|healthcare|畜牧|手办|盲盒|action\s*figure",
        r"关键词|keyword",
        r"listing|商品|卖家|店铺|shop",
        r"VN|SG|MY|TH|PH|站点",
        r"价格|price",
        r"大盘|趋势|市场",
    )
)


def normalize_understanding_readiness(
    spec: RequirementUnderstandingSpec,
) -> RequirementUnderstandingSpec:
    """Apply deterministic rules so non-blocking ambiguities do not block progress."""
    updated = spec.model_copy(deep=True)
    text = _combined_text(updated)

    if _matches_any(text, WAIT_FOR_USER_PATTERNS):
        updated.status = UnderstandingStatus.NEEDS_MINIMUM_CONTEXT
        updated.readiness.can_select_modules = False
        updated.readiness.blocking_reasons = _unique(
            updated.readiness.blocking_reasons
            + ["用户明确表示先等待确认，暂不进入 module selection。"]
        )
        return updated

    if updated.status == UnderstandingStatus.OUT_OF_SCOPE:
        if _is_market_related(text) and _has_analysis_object_clues(updated, text):
            updated.status = UnderstandingStatus.READY_FOR_MODULE_SELECTION
        else:
            updated.readiness.can_select_modules = False
            updated.readiness.blocking_reasons = _unique(
                updated.readiness.blocking_reasons
                + ["需求与 CateMate 类目分析无关。"]
            )
            return updated

    _demote_non_blocking_items(updated)

    if updated.status == UnderstandingStatus.NEEDS_MINIMUM_CONTEXT:
        if _is_market_related(text) and _has_analysis_object_clues(updated, text):
            updated.status = UnderstandingStatus.READY_FOR_MODULE_SELECTION
            updated.readiness.blocking_reasons = [
                r for r in updated.readiness.blocking_reasons if "最小上下文" not in r
            ]

    if _is_market_related(text) and _has_analysis_object_clues(updated, text):
        updated.status = UnderstandingStatus.READY_FOR_MODULE_SELECTION
        updated.readiness.can_select_modules = True
        updated.readiness.blocking_reasons = [
            reason
            for reason in updated.readiness.blocking_reasons
            if not _is_non_blocking_topic(reason)
        ]
    elif not _is_market_related(text) and _matches_any(text, OUT_OF_SCOPE_PATTERNS):
        updated.status = UnderstandingStatus.OUT_OF_SCOPE
        updated.readiness.can_select_modules = False
        return updated
    elif not _has_analysis_object_clues(updated, text):
        updated.status = UnderstandingStatus.NEEDS_MINIMUM_CONTEXT
        updated.readiness.can_select_modules = False
        updated.readiness.blocking_reasons = _unique(
            updated.readiness.blocking_reasons
            + ["完全无法判断分析对象（类目/商品/关键词/站点/卖家/业务背景均无可用线索）。"]
        )
        return updated

    blocking_questions = [q for q in updated.clarifying_questions if q.blocks_module_selection]
    blocking_uncertainties = [u for u in updated.uncertainties if u.blocks_module_selection]

    if not blocking_questions and not blocking_uncertainties:
        updated.readiness.can_select_modules = True
        if updated.status != UnderstandingStatus.OUT_OF_SCOPE:
            updated.status = UnderstandingStatus.READY_FOR_MODULE_SELECTION

    non_blocking_notes = list(updated.readiness.non_blocking_notes)
    for item in updated.uncertainties:
        if not item.blocks_module_selection:
            note = f"{item.topic}: {item.description}"
            if note not in non_blocking_notes:
                non_blocking_notes.append(note)
    updated.readiness.non_blocking_notes = non_blocking_notes

    if updated.readiness.can_select_modules and updated.status != UnderstandingStatus.OUT_OF_SCOPE:
        updated.status = UnderstandingStatus.READY_FOR_MODULE_SELECTION
        updated.readiness.blocking_reasons = []

    return updated


def _demote_non_blocking_items(spec: RequirementUnderstandingSpec) -> None:
    for question in spec.clarifying_questions:
        if _is_non_blocking_topic(question.question) or _is_non_blocking_topic(question.reason):
            question.blocks_module_selection = False
    for uncertainty in spec.uncertainties:
        if _is_non_blocking_topic(uncertainty.topic) or _is_non_blocking_topic(uncertainty.description):
            uncertainty.blocks_module_selection = False


def _is_non_blocking_topic(text: str) -> bool:
    return _matches_any(text, NON_BLOCKING_TOPIC_PATTERNS)


def _is_market_related(text: str) -> bool:
    return _matches_any(text, MARKET_RELEVANCE_PATTERNS)


def _has_analysis_object_clues(spec: RequirementUnderstandingSpec, text: str) -> bool:
    understood = spec.understood
    if understood.target_category_text.strip():
        return True
    if understood.inferred_category.strip():
        return True
    if understood.target_sites:
        return True
    intents = [intent for intent in understood.analysis_intents if intent.value != "unknown"]
    if intents:
        return True
    if understood.business_background.strip() and understood.business_background.strip() != "待确认":
        return True
    if _matches_any(text, ANALYSIS_OBJECT_PATTERNS):
        return True
    return False


def _combined_text(spec: RequirementUnderstandingSpec) -> str:
    parts = [
        spec.original_request,
        spec.conversation_summary,
        spec.understood.target_category_text,
        spec.understood.inferred_category,
        spec.understood.business_background,
        " ".join(spec.understood.target_sites),
        " ".join(intent.value for intent in spec.understood.analysis_intents),
    ]
    for assumption in spec.assumptions:
        parts.append(assumption.content)
    for answer in spec.user_answers:
        parts.append(answer.answer)
    return "\n".join(p for p in parts if p)


def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
