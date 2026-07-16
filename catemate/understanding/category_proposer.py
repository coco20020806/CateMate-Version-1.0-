"""Propose top-K category candidates for human confirmation."""

from __future__ import annotations

from catemate.data.category_tree_en import CategoryTreePath, cached_category_paths
from catemate.understanding.category_mapper import (
    MIN_MATCH_SCORE,
    _normalize_text,
    _rank_paths,
    _score_path,
)
from catemate.understanding.schemas import ConfidenceLevel, InferredCategoryCandidate


def propose_category_candidates(
    *,
    request_text: str,
    category_text: str = "",
    top_k: int = 5,
    min_score: float = MIN_MATCH_SCORE,
) -> list[InferredCategoryCandidate]:
    """Return ranked category candidates; includes near-misses when none meet min_score."""
    combined = f"{request_text} {category_text}".strip()
    normalized = _normalize_text(combined)
    if not normalized:
        return []

    paths = list(cached_category_paths())
    ranked: list[tuple[CategoryTreePath, float]] = []
    for path in paths:
        score = _score_path(normalized, path)
        if score > 0:
            ranked.append((path, score))
    ranked.sort(key=lambda item: item[1], reverse=True)

    seen_paths: set[str] = set()
    candidates: list[InferredCategoryCandidate] = []
    for path, score in ranked:
        category_path = path.path
        if category_path in seen_paths:
            continue
        seen_paths.add(category_path)
        candidates.append(_path_to_candidate(path, score, min_score=min_score))
        if len(candidates) >= top_k:
            break
    return candidates


def derive_positioning_type(
    candidates: list[InferredCategoryCandidate],
    *,
    min_score: float = MIN_MATCH_SCORE,
) -> str:
    """Return single_category | multi_category | unresolved based on above-threshold count."""
    above = [c for c in candidates if _score_from_reason(c.reason) >= min_score]
    if len(above) >= 2:
        return "multi_category"
    if len(above) == 1:
        return "single_category"
    if candidates:
        return "unresolved"
    return "unresolved"


def _path_to_candidate(
    path: CategoryTreePath,
    score: float,
    *,
    min_score: float,
) -> InferredCategoryCandidate:
    if path.l3:
        level = "L3"
    elif path.l2:
        level = "L2"
    else:
        level = "L1"

    if score >= 0.75:
        confidence = ConfidenceLevel.HIGH
    elif score >= min_score:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW

    threshold_note = "达到阈值" if score >= min_score else "低于阈值（near-miss）"
    return InferredCategoryCandidate(
        l1=path.l1,
        l2=path.l2,
        l3=path.l3,
        category_path=path.path,
        reason=f"{level} 匹配分数 {score:.2f}（{threshold_note}）",
        confidence=confidence,
    )


def _score_from_reason(reason: str) -> float:
    marker = "匹配分数"
    if marker not in reason:
        return 0.0
    fragment = reason.split(marker, 1)[1].strip()
    num = ""
    for char in fragment:
        if char.isdigit() or char == ".":
            num += char
        elif num:
            break
    try:
        return float(num)
    except ValueError:
        return 0.0
