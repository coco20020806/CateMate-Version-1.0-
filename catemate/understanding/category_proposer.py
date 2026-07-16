"""Propose top-K category candidates for human confirmation."""

from __future__ import annotations

from catemate.data.category_tree_en import CategoryTreePath
from catemate.understanding.category_mapper import (
    MIN_MATCH_SCORE,
    _normalize_text,
    is_strict_ancestor_path,
    rank_paths_by_depth,
)
from catemate.understanding.schemas import ConfidenceLevel, InferredCategoryCandidate


def propose_category_candidates(
    *,
    request_text: str,
    category_text: str = "",
    top_k: int = 5,
    min_score: float = MIN_MATCH_SCORE,
) -> list[InferredCategoryCandidate]:
    """Return ranked category candidates with deepest-match-first and ancestor pruning."""
    combined = f"{request_text} {category_text}".strip()
    normalized = _normalize_text(combined)
    if not normalized:
        return []

    from catemate.data.category_tree_en import cached_category_paths

    ranked = rank_paths_by_depth(normalized, list(cached_category_paths()))
    candidates = [
        _path_to_candidate(path, depth=depth, score=score, min_score=min_score)
        for path, depth, score in ranked
    ]
    pruned = prune_ancestor_candidates(candidates)
    return pruned[:top_k]


def merge_candidates(
    primary: list[InferredCategoryCandidate],
    secondary: list[InferredCategoryCandidate],
) -> list[InferredCategoryCandidate]:
    """Merge candidate lists with primary entries first; dedupe by category_path."""
    seen: set[str] = set()
    merged: list[InferredCategoryCandidate] = []
    for candidate in [*primary, *secondary]:
        key = candidate.category_path or _candidate_path_key(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(candidate)
    return merged


def prune_ancestor_candidates(
    candidates: list[InferredCategoryCandidate],
) -> list[InferredCategoryCandidate]:
    """Drop ancestor paths when a deeper descendant is already selected."""
    result: list[InferredCategoryCandidate] = []
    result_paths: list[str] = []
    for candidate in candidates:
        path = candidate.category_path or _candidate_path_key(candidate)
        if not path:
            continue
        if any(is_strict_ancestor_path(path, selected) for selected in result_paths):
            continue
        result.append(candidate)
        result_paths.append(path)
    return result


def derive_positioning_type(
    candidates: list[InferredCategoryCandidate],
    *,
    min_score: float = MIN_MATCH_SCORE,
) -> str:
    """Return single_category | multi_category | unresolved based on above-threshold count."""
    above = [
        candidate
        for candidate in candidates
        if _depth_from_reason(candidate.reason) > 0
        and _score_from_reason(candidate.reason) >= min_score
    ]
    if len(above) >= 2:
        return "multi_category"
    if len(above) == 1:
        return "single_category"
    if candidates:
        return "unresolved"
    return "unresolved"


def _path_to_candidate(
    path: CategoryTreePath,
    *,
    depth: int,
    score: float,
    min_score: float,
) -> InferredCategoryCandidate:
    level = {1: "L1", 2: "L2", 3: "L3"}.get(depth, "L1")

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
        reason=f"{level} matched_depth={depth} 匹配分数 {score:.2f}（{threshold_note}）",
        confidence=confidence,
    )


def _candidate_path_key(candidate: InferredCategoryCandidate) -> str:
    return " > ".join(part for part in [candidate.l1, candidate.l2, candidate.l3] if part)


def _depth_from_reason(reason: str) -> int:
    marker = "matched_depth="
    if marker not in reason:
        return 0
    fragment = reason.split(marker, 1)[1]
    digits = ""
    for char in fragment:
        if char.isdigit():
            digits += char
        elif digits:
            break
    try:
        return int(digits)
    except ValueError:
        return 0


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
