"""Map natural-language category requests onto category_tree_en.json paths."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from catemate.data.category_tree_en import CategoryTreePath, cached_category_paths, find_path_in_tree
from catemate.understanding.schemas import (
    ConfidenceLevel,
    InferredCategoryCandidate,
    RequirementUnderstandingSpec,
    RequirementReadiness,
    SubL3Concept,
    UnderstandingStatus,
)
from catemate.understanding.sub_l3_detector import has_sub_l3_qualifiers, infer_sub_l3_concept

MappedLevel = Literal["L1", "L2", "L3"]

TERM_ALIASES: dict[str, str] = {
    "智能宠物碗": "smart pet bowl feeder",
    "宠物碗": "pet bowl",
    "喂食器": "feeder",
    "饮水器": "feeder",
    "喂水器": "feeder",
    "碗": "bowl",
    "狗粮": "dog food",
    "猫粮": "cat food",
    "宠物主粮": "pet food",
    "主粮": "pet food",
    "宠物食品": "pet food",
    "宠物粮": "pet food",
    "宠物": "pets",
    "宠物品类": "pets",
    "宠物类目": "pets",
    "猫食": "cat food",
    "狗食": "dog food",
    "文具": "stationery",
    "书": "books",
    "图书": "books",
    "爱好": "hobbies",
    "收藏": "collections",
}

GENERIC_L1_TERMS = frozenset({"pets", "stationery", "hobbies", "collections", "books"})

SPECIFIC_PRODUCT_TERMS = frozenset(
    {
        "bowl",
        "bowls",
        "feeder",
        "feeders",
        "smart",
        "automatic",
        "auto",
        "electric",
        "dog",
        "cat",
        "food",
        "treat",
        "treats",
        "grooming",
        "healthcare",
        "accessories",
        "clothing",
        "litter",
        "medication",
        "vitamin",
        "supplement",
        "aquarium",
        "stationery",
        "pen",
        "book",
        "books",
    }
)

BROAD_PET_FOOD_TERMS = {
    "pet food",
    "宠物主粮",
    "主粮",
    "宠物食品",
    "宠物粮",
}

SPECIFIC_PET_FOOD_TERMS = {
    "dog food",
    "cat food",
    "狗粮",
    "猫粮",
    "狗食",
    "猫食",
    "dog treat",
    "cat treat",
}

MIN_MATCH_SCORE = 0.42

TOKEN_STOP_WORDS = frozenset({"pet", "pets", "other", "others", "and", "the"})


@dataclass(frozen=True)
class CategoryMappingResult:
    is_relevant: bool
    mapped_level: MappedLevel | None = None
    l1: str = ""
    l2: str = ""
    l3: str = ""
    category_path: str = ""
    reason: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    has_sub_l3_qualifiers: bool = False


def resolve_category_mapping(
    *,
    request_text: str,
    category_text: str = "",
) -> CategoryMappingResult:
    """Resolve the deepest valid L1/L2/L3 mapping, or mark input as irrelevant."""
    combined = f"{request_text} {category_text}".strip()
    normalized = _normalize_text(combined)
    if not normalized:
        return CategoryMappingResult(is_relevant=False, reason="需求文本为空，无法映射类目。")

    if _is_broad_category_request(request_text, category_text):
        for path in cached_category_paths():
            if path.depth != 1:
                continue
            score = _score_node(normalized, path.l1, weight=1.0)
            if score >= MIN_MATCH_SCORE:
                return _build_result(path, mapped_level="L1", score=score, reason="需求仅明确到 L1 类目")

    if _is_broad_pet_food_request(request_text, category_text, normalized):
        pet_food_l2 = find_path_in_tree("Pets", "Pet Food", "")
        if pet_food_l2:
            return _build_result(
                pet_food_l2,
                mapped_level="L2",
                score=0.9,
                reason="需求覆盖整个 L2 类目范围",
            )

    ranked = rank_paths_by_depth(normalized, list(cached_category_paths()))
    if not ranked:
        return CategoryMappingResult(
            is_relevant=False,
            reason="无法在 category_tree_en.json 中找到与需求相关的 L1/L2/L3 类目，判定为无关输入。",
            confidence=ConfidenceLevel.LOW,
        )

    best_path, best_depth, best_score = ranked[0]

    if best_depth == 3 and best_score >= MIN_MATCH_SCORE:
        if _should_use_l2_instead_of_l3(normalized, best_path):
            parent_l2 = find_path_in_tree(best_path.l1, best_path.l2, "")
            if parent_l2:
                return _build_result(
                    parent_l2,
                    mapped_level="L2",
                    score=best_score,
                    reason="需求覆盖整个 L2 类目范围",
                )
        return _build_result(
            best_path,
            mapped_level="L3",
            score=best_score,
            reason="需求可高概率由该 L3 覆盖",
            request_text=normalized,
        )

    if best_depth == 2 and best_score >= MIN_MATCH_SCORE:
        return _build_result(
            best_path,
            mapped_level="L2",
            score=best_score,
            reason="需求覆盖整个 L2 类目范围",
        )

    if best_depth == 1 and best_score >= MIN_MATCH_SCORE:
        return _build_result(
            best_path,
            mapped_level="L1",
            score=best_score,
            reason="需求仅明确到 L1 类目",
        )

    return CategoryMappingResult(
        is_relevant=False,
        reason="无法在 category_tree_en.json 中找到与需求相关的 L1/L2/L3 类目，判定为无关输入。",
        confidence=ConfidenceLevel.LOW,
    )


def apply_category_mapping(
    spec: RequirementUnderstandingSpec,
    mapping: CategoryMappingResult,
) -> RequirementUnderstandingSpec:
    if not mapping.is_relevant or not mapping.mapped_level:
        return spec.model_copy(
            update={
                "status": UnderstandingStatus.OUT_OF_SCOPE,
                "conversation_summary": (
                    spec.conversation_summary
                    + " "
                    + (mapping.reason or "无关输入，流程终止。")
                ).strip(),
                "readiness": RequirementReadiness(
                    can_select_modules=False,
                    blocking_reasons=[mapping.reason or "无关输入"],
                    non_blocking_notes=spec.readiness.non_blocking_notes,
                ),
            }
        )

    candidate = InferredCategoryCandidate(
        l1=mapping.l1,
        l2=mapping.l2,
        l3=mapping.l3,
        category_path=mapping.category_path,
        reason=mapping.reason,
        confidence=mapping.confidence,
    )
    understood = spec.understood.model_copy(
        update={
            "inferred_category": mapping.category_path,
            "inferred_category_candidates": [candidate],
            "category_level_hint": mapping.mapped_level,
        }
    )
    if mapping.mapped_level == "L3" and mapping.has_sub_l3_qualifiers:
        sub_l3 = infer_sub_l3_concept(
            spec.model_copy(
                update={
                    "understood": understood.model_copy(
                        update={"sub_l3_concept": SubL3Concept(is_sub_l3=True)}
                    )
                }
            )
        )
        if not sub_l3.parent_l3:
            sub_l3 = sub_l3.model_copy(update={"parent_l3": mapping.l3})
        understood = understood.model_copy(update={"sub_l3_concept": sub_l3})
    return spec.model_copy(update={"understood": understood})


def enforce_category_mapping(spec: RequirementUnderstandingSpec) -> CategoryMappingResult:
    """Validate existing candidates or remap from request text."""
    understood = spec.understood
    for candidate in understood.inferred_category_candidates:
        validated = find_path_in_tree(candidate.l1, candidate.l2, candidate.l3)
        if validated is not None:
            level: MappedLevel
            if validated.l3:
                level = "L3"
            elif validated.l2:
                level = "L2"
            else:
                level = "L1"
            return CategoryMappingResult(
                is_relevant=True,
                mapped_level=level,
                l1=validated.l1,
                l2=validated.l2,
                l3=validated.l3,
                category_path=validated.path,
                reason=candidate.reason or "沿用理解层给出的类目候选",
                confidence=candidate.confidence,
            )

    return resolve_category_mapping(
        request_text=spec.original_request,
        category_text=understood.target_category_text or understood.inferred_category,
    )


def _build_result(
    path: CategoryTreePath,
    *,
    mapped_level: MappedLevel,
    score: float,
    reason: str,
    request_text: str = "",
) -> CategoryMappingResult:
    confidence = ConfidenceLevel.HIGH if score >= 0.75 else ConfidenceLevel.MEDIUM
    return CategoryMappingResult(
        is_relevant=True,
        mapped_level=mapped_level,
        l1=path.l1,
        l2=path.l2 if mapped_level in {"L2", "L3"} else "",
        l3=path.l3 if mapped_level == "L3" else "",
        category_path=" > ".join(
            part
            for part in [
                path.l1,
                path.l2 if mapped_level in {"L2", "L3"} else "",
                path.l3 if mapped_level == "L3" else "",
            ]
            if part
        ),
        reason=reason,
        confidence=confidence,
        has_sub_l3_qualifiers=mapped_level == "L3" and has_sub_l3_qualifiers(request_text),
    )


def _should_use_l2_instead_of_l3(normalized: str, path: CategoryTreePath) -> bool:
    if not path.l3 or not path.l2:
        return False
    if _is_broad_pet_food_request("", "", normalized) and path.l2.lower() == "pet food":
        return True
    if path.l2.lower() != "pet food":
        return False
    has_broad = any(term in normalized for term in BROAD_PET_FOOD_TERMS)
    has_specific = any(term in normalized for term in SPECIFIC_PET_FOOD_TERMS)
    if has_broad and not has_specific:
        return True
    l3_name = path.l3.lower()
    if has_specific:
        if "dog" in normalized or "狗粮" in normalized or "狗" in normalized:
            return l3_name != "dog food" and "dog" not in l3_name
        if "cat" in normalized or "猫粮" in normalized or "猫" in normalized:
            return l3_name != "cat food" and "cat" not in l3_name
    return False


def _is_broad_category_request(request_text: str, category_text: str) -> bool:
    combined = f"{request_text} {category_text}"
    broad_markers = ("类目", "品类", "category", "大类")
    if not any(marker in combined for marker in broad_markers):
        return False
    specific_markers = (
        "狗粮",
        "猫粮",
        "dog food",
        "cat food",
        "主粮",
        "treat",
        "grooming",
        "healthcare",
        "clothing",
        "accessories",
    )
    lowered = combined.lower()
    return not any(marker in combined or marker in lowered for marker in specific_markers)


def _is_broad_pet_food_request(request_text: str, category_text: str, normalized: str) -> bool:
    combined = f"{request_text} {category_text}"
    has_broad = any(term in combined or term in normalized for term in BROAD_PET_FOOD_TERMS)
    has_specific = any(term in combined or term in normalized for term in SPECIFIC_PET_FOOD_TERMS)
    return has_broad and not has_specific


def rank_paths_by_depth(
    normalized: str,
    paths: list[CategoryTreePath],
) -> list[tuple[CategoryTreePath, int, float]]:
    """Rank paths by deepest match first, then score within that depth."""
    ranked: list[tuple[CategoryTreePath, int, float]] = []
    for path in paths:
        depth, score = path_match_key(normalized, path)
        if depth > 0 and score > 0:
            ranked.append((path, depth, score))
    ranked.sort(key=lambda item: (item[1], item[2]), reverse=True)
    return ranked


def path_match_key(normalized: str, path: CategoryTreePath) -> tuple[int, float]:
    """Return the deepest level with a positive match score for this path."""
    for depth, name, weight in (
        (3, path.l3, 1.5),
        (2, path.l2, 1.2),
        (1, path.l1, 1.0),
    ):
        if not name:
            continue
        score = _score_node(normalized, name, weight=weight)
        if score <= 0:
            continue
        if depth == 1 and _is_generic_l1_only_match(normalized, name):
            continue
        return depth, score
    return 0, 0.0


def is_strict_ancestor_path(ancestor_path: str, descendant_path: str) -> bool:
    """True when ancestor_path is a strict prefix of descendant_path."""
    ancestor = ancestor_path.strip()
    descendant = descendant_path.strip()
    if not ancestor or not descendant or ancestor == descendant:
        return False
    return descendant.startswith(f"{ancestor} > ")


def _is_generic_l1_only_match(normalized: str, l1_name: str) -> bool:
    node_norm = _normalize_text(l1_name)
    if node_norm not in GENERIC_L1_TERMS:
        return False
    return _has_specific_product_terms(normalized)


def _has_specific_product_terms(normalized: str) -> bool:
    tokens = set(_tokenize(normalized))
    if tokens & SPECIFIC_PRODUCT_TERMS:
        return True
    return any(term in normalized for term in ("智能", "自动", "电动"))


def _score_node(normalized: str, node_name: str, *, weight: float) -> float:
    node_norm = _normalize_text(node_name)
    if not node_norm:
        return 0.0
    if node_norm in normalized:
        return 1.0 * weight
    node_tokens = _meaningful_token_set(node_norm)
    req_tokens = _meaningful_token_set(normalized)
    if not node_tokens:
        return 0.0
    overlap = len(_token_overlap(node_tokens, req_tokens)) / len(node_tokens)
    return overlap * weight


def _meaningful_token_set(text: str) -> set[str]:
    return {token for token in _tokenize(text) if token not in TOKEN_STOP_WORDS and len(token) > 1}


def _token_overlap(left: set[str], right: set[str]) -> set[str]:
    matched: set[str] = set()
    for left_token in left:
        left_variants = _token_variants(left_token)
        for right_token in right:
            if left_variants & _token_variants(right_token):
                matched.add(left_token)
                break
    return matched


def _token_variants(token: str) -> set[str]:
    variants = {token}
    if token.endswith("s") and len(token) > 3:
        variants.add(token[:-1])
    elif not token.endswith("s"):
        variants.add(f"{token}s")
    return variants


def _normalize_text(text: str) -> str:
    lowered = text.lower().strip()
    for zh, en in sorted(TERM_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        lowered = lowered.replace(zh.lower(), f" {en} ")
    lowered = re.sub(r"[^\w\s&]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[\s/>,]+", text) if token]
