"""Detect when a user request is more specific than the mapped L3 category."""

from __future__ import annotations

import re

from catemate.understanding.schemas import RequirementUnderstandingSpec, SubL3Concept

SUB_L3_QUALIFIER_TERMS = (
    "smart",
    "automatic",
    "auto",
    "electric",
    "wireless",
    "wifi",
    "bluetooth",
    "sensor",
    "app",
    "programmable",
    "timer",
    "premium",
    "organic",
    "portable",
    "mini",
    "large capacity",
    "stainless",
    "智能",
    "自动",
    "电动",
    "无线",
    "蓝牙",
    "感应",
    "定时",
    "便携",
    "迷你",
    "不锈钢",
    "大容量",
)


def has_sub_l3_qualifiers(text: str) -> bool:
    """Return True when text contains qualifiers beyond a plain category name."""
    normalized = _normalize(text)
    if not normalized:
        return False
    return any(_term_in_text(term, normalized) for term in SUB_L3_QUALIFIER_TERMS)


def should_generate_concept_pack(spec: RequirementUnderstandingSpec) -> bool:
    """Decide whether if_related concept pack generation should run."""
    understood = spec.understood
    if understood.sub_l3_concept.is_sub_l3:
        return True

    if understood.category_level_hint != "L3":
        return False

    combined = " ".join(
        part
        for part in [
            spec.original_request,
            understood.target_category_text,
            understood.inferred_category,
        ]
        if part
    )
    if not has_sub_l3_qualifiers(combined):
        return False

    l3_name = ""
    if understood.inferred_category_candidates:
        l3_name = understood.inferred_category_candidates[0].l3
    return _request_narrower_than_l3(combined, l3_name)


def infer_sub_l3_concept(spec: RequirementUnderstandingSpec) -> SubL3Concept:
    """Build sub-L3 metadata when qualifiers indicate a narrower concept."""
    understood = spec.understood
    if understood.sub_l3_concept.is_sub_l3:
        return understood.sub_l3_concept

    parent_l3 = ""
    if understood.inferred_category_candidates:
        parent_l3 = understood.inferred_category_candidates[0].l3

    display_name = understood.target_category_text.strip() or _extract_display_name(spec.original_request)
    concept_id = _slugify(display_name) or "sub_l3_concept"

    return SubL3Concept(
        is_sub_l3=True,
        concept_id=concept_id,
        display_name=display_name,
        parent_l3=parent_l3,
    )


def _request_narrower_than_l3(text: str, l3_name: str) -> bool:
    normalized = _normalize(text)
    if not normalized or not has_sub_l3_qualifiers(normalized):
        return False
    if not l3_name.strip():
        return True

    l3_norm = _normalize(l3_name)
    l3_tokens = set(_tokenize(l3_norm))
    req_tokens = set(_tokenize(normalized))
    extra_tokens = req_tokens - l3_tokens
    qualifier_tokens = {
        token
        for term in SUB_L3_QUALIFIER_TERMS
        for token in _tokenize(_normalize(term))
        if token
    }
    return bool(extra_tokens & qualifier_tokens) or len(req_tokens) > len(l3_tokens) + 2


def _extract_display_name(request_text: str) -> str:
    cleaned = request_text.strip()
    for prefix in ("分析", "看看", "帮我分析", "请分析"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    for suffix in ("市场", "趋势", "表现", "情况"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned or request_text.strip()


def _slugify(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^\w\s]+", " ", lowered, flags=re.UNICODE)
    tokens = [token for token in lowered.split() if token]
    if not tokens:
        return ""
    return "_".join(tokens)[:64]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[\s/>,&]+", text) if token]


def _term_in_text(term: str, normalized_text: str) -> bool:
    term_norm = _normalize(term)
    if not term_norm:
        return False
    if " " in term_norm:
        return term_norm in normalized_text
    return re.search(rf"\b{re.escape(term_norm)}\b", normalized_text) is not None or term_norm in normalized_text
