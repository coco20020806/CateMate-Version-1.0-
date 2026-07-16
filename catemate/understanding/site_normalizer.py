"""Normalize target_sites: empty list means all sites."""

from __future__ import annotations

import re

from catemate.understanding.schemas import RequirementUnderstandingSpec

KNOWN_SITE_CODES = ("AR", "BR", "CL", "CO", "ID", "MX", "MY", "PH", "SG", "TH", "TW", "VN")

ALL_SITES_MARKERS = (
    "全部站点",
    "所有站点",
    "各站点",
    "全站点",
    "所有市场",
    "全部市场",
    "all sites",
    "all regions",
    "all markets",
)

SITE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), code)
    for pattern, code in (
        (r"\bvn\b", "VN"),
        (r"越南", "VN"),
        (r"vietnam", "VN"),
        (r"\bsg\b", "SG"),
        (r"新加坡", "SG"),
        (r"singapore", "SG"),
        (r"\bmy\b", "MY"),
        (r"马来西亚", "MY"),
        (r"malaysia", "MY"),
        (r"\bth\b", "TH"),
        (r"泰国", "TH"),
        (r"thailand", "TH"),
        (r"\bph\b", "PH"),
        (r"菲律宾", "PH"),
        (r"philippines", "PH"),
        (r"\bid\b", "ID"),
        (r"印尼", "ID"),
        (r"印度尼西亚", "ID"),
        (r"indonesia", "ID"),
        (r"\bbr\b", "BR"),
        (r"巴西", "BR"),
        (r"brazil", "BR"),
        (r"\btw\b", "TW"),
        (r"台湾", "TW"),
        (r"taiwan", "TW"),
        (r"\bmx\b", "MX"),
        (r"墨西哥", "MX"),
        (r"mexico", "MX"),
        (r"\bcl\b", "CL"),
        (r"智利", "CL"),
        (r"chile", "CL"),
        (r"\bco\b", "CO"),
        (r"哥伦比亚", "CO"),
        (r"colombia", "CO"),
        (r"\bar\b", "AR"),
        (r"阿根廷", "AR"),
        (r"argentina", "AR"),
    )
)


def extract_target_sites_from_text(text: str) -> list[str]:
    """Return explicit site codes mentioned in text; empty means all sites."""
    text = (text or "").strip()
    if not text:
        return []
    lowered = text.lower()
    if any(marker in lowered for marker in ALL_SITES_MARKERS):
        return []

    found: list[str] = []
    for pattern, code in SITE_PATTERNS:
        if pattern.search(text) and code not in found:
            found.append(code)
    return found


def site_source_text(spec: RequirementUnderstandingSpec) -> str:
    parts = [spec.original_request]
    for answer in spec.user_answers:
        if answer.answer.strip() and answer.answer != "[skipped]":
            parts.append(answer.answer)
    return "\n".join(part for part in parts if part.strip())


def normalize_target_sites(spec: RequirementUnderstandingSpec) -> RequirementUnderstandingSpec:
    """If the user did not name a site, clear target_sites so scope uses all sites."""
    detected = extract_target_sites_from_text(site_source_text(spec))
    understood = spec.understood.model_copy(update={"target_sites": detected})
    return spec.model_copy(update={"understood": understood})


def normalize_case_config_target_sites(
    target_sites: list[str],
    *,
    request_text: str,
) -> list[str]:
    return extract_target_sites_from_text(request_text)
