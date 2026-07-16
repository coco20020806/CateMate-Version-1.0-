"""Category positioning confirmation gate helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from catemate.ai.client import CateMateAIClient
from catemate.data.category_tree_en import find_path_in_tree
from catemate.understanding.category_mapper import (
    CategoryMappingResult,
    apply_category_mapping,
)
from catemate.understanding.category_proposer import (
    derive_positioning_type,
    merge_candidates,
    prune_ancestor_candidates,
    propose_category_candidates,
)
from catemate.understanding.concept_pack_generator import enrich_understanding_with_related_concept
from catemate.understanding.generator import _validate_spec
from catemate.understanding.prompt_builder import build_requirement_understanding_messages
from catemate.understanding.schemas import (
    CategoryFeedbackRound,
    CategoryPositioning,
    ConfidenceLevel,
    InferredCategoryCandidate,
    RequirementUnderstandingSpec,
)
from catemate.understanding.sub_l3_detector import has_sub_l3_qualifiers

PositioningType = Literal["single_category", "multi_category", "unresolved"]

CATEGORY_FEEDBACK_QUESTION_ID = "category_feedback"


def is_category_confirmation_complete(spec: RequirementUnderstandingSpec) -> bool:
    """True when user has confirmed category selection, or legacy spec without gate."""
    positioning = spec.understood.category_positioning
    if positioning.confirmed:
        return True
    if not positioning.proposed_candidates and spec.understood.inferred_category_candidates:
        return True
    return False


def can_confirm_selection(selected_paths: list[str]) -> bool:
    return len(selected_paths) >= 1


def candidate_key(candidate: InferredCategoryCandidate) -> str:
    return candidate.category_path or " > ".join(
        part for part in [candidate.l1, candidate.l2, candidate.l3] if part
    )


def initialize_category_positioning(spec: RequirementUnderstandingSpec) -> RequirementUnderstandingSpec:
    request_text, category_text = _build_proposal_context(spec)
    ai_candidates = _validated_ai_candidates(spec)
    proposed = propose_category_candidates(
        request_text=request_text,
        category_text=category_text,
    )
    proposed = prune_ancestor_candidates(merge_candidates(ai_candidates, proposed))
    positioning = CategoryPositioning(
        positioning_type=derive_positioning_type(proposed),  # type: ignore[arg-type]
        proposed_candidates=proposed,
        confirmed=False,
    )
    understood = spec.understood.model_copy(update={"category_positioning": positioning})
    return spec.model_copy(update={"understood": understood})


def apply_category_feedback(
    spec: RequirementUnderstandingSpec,
    feedback: str,
    ai_client: CateMateAIClient | None = None,
) -> RequirementUnderstandingSpec:
    feedback = feedback.strip()
    if not feedback:
        return spec

    now = datetime.now(timezone.utc).isoformat()
    positioning = spec.understood.category_positioning
    rounds = list(positioning.feedback_rounds)
    rounds.append(CategoryFeedbackRound(user_feedback=feedback, answered_at=now))

    updated = spec
    if ai_client is not None:
        messages = build_requirement_understanding_messages(
            request_text=spec.original_request,
            previous_spec=spec.model_dump(mode="json"),
            user_answers=[
                {
                    "question_id": CATEGORY_FEEDBACK_QUESTION_ID,
                    "question": "请根据用户对类目判断的反馈，更新类目理解与候选。",
                    "answer": feedback,
                    "skipped": False,
                    "default_assumption": "",
                    "answered_at": now,
                }
            ],
        )
        payload = ai_client.complete_json(messages)
        updated = _validate_spec(payload, original_request=spec.original_request)

    request_text, category_text = _build_proposal_context(updated, feedback=feedback)
    ai_candidates = _validated_ai_candidates(updated)
    proposed = propose_category_candidates(
        request_text=request_text,
        category_text=category_text,
    )
    proposed = prune_ancestor_candidates(merge_candidates(ai_candidates, proposed))
    summary = _feedback_summary(proposed)
    if rounds:
        rounds[-1] = rounds[-1].model_copy(update={"system_summary": summary})

    positioning = CategoryPositioning(
        positioning_type=derive_positioning_type(proposed),  # type: ignore[arg-type]
        proposed_candidates=proposed,
        confirmed=False,
        feedback_rounds=rounds,
    )
    understood = updated.understood.model_copy(update={"category_positioning": positioning})
    return updated.model_copy(update={"understood": understood})


def _build_proposal_context(
    spec: RequirementUnderstandingSpec,
    *,
    feedback: str = "",
) -> tuple[str, str]:
    understood = spec.understood
    parts = [
        spec.original_request,
        feedback,
        understood.inferred_category,
        understood.target_category_text,
    ]
    request_text = " ".join(part.strip() for part in parts if part and part.strip())
    category_text = understood.inferred_category.strip() or understood.target_category_text.strip()
    return request_text, category_text


def _validated_ai_candidates(spec: RequirementUnderstandingSpec) -> list[InferredCategoryCandidate]:
    validated: list[InferredCategoryCandidate] = []
    for candidate in spec.understood.inferred_category_candidates:
        path = find_path_in_tree(candidate.l1, candidate.l2, candidate.l3)
        if path is None:
            continue
        validated.append(
            candidate.model_copy(
                update={
                    "l1": path.l1,
                    "l2": path.l2,
                    "l3": path.l3,
                    "category_path": path.path,
                }
            )
        )
    return validated


def _feedback_summary(proposed: list[InferredCategoryCandidate]) -> str:
    if not proposed:
        return "已根据反馈更新，但当前没有可用类目候选，请补充更明确的类目描述。"
    paths = "、".join(candidate_key(item) for item in proposed[:3])
    suffix = "…" if len(proposed) > 3 else ""
    return f"已根据反馈更新，当前提案 {len(proposed)} 个类目候选：{paths}{suffix}"


def confirm_categories(
    spec: RequirementUnderstandingSpec,
    selected_paths: list[str],
) -> RequirementUnderstandingSpec:
    if not can_confirm_selection(selected_paths):
        raise ValueError("至少勾选 1 个类目候选才能确认。")

    selected_set = {path.strip() for path in selected_paths if path.strip()}
    proposed = spec.understood.category_positioning.proposed_candidates
    confirmed = [
        candidate
        for candidate in proposed
        if candidate_key(candidate) in selected_set
    ]
    if not confirmed:
        raise ValueError("勾选的类目不在当前提案列表中。")

    positioning = spec.understood.category_positioning.model_copy(
        update={
            "confirmed_candidates": confirmed,
            "confirmed": True,
        }
    )
    understood = spec.understood.model_copy(update={"category_positioning": positioning})
    return spec.model_copy(update={"understood": understood})


def finalize_after_category_confirmation(
    spec: RequirementUnderstandingSpec,
    ai_client: CateMateAIClient | None = None,
) -> RequirementUnderstandingSpec:
    if not is_category_confirmation_complete(spec):
        raise ValueError("类目尚未确认，无法 finalize。")

    positioning = spec.understood.category_positioning
    confirmed = positioning.confirmed_candidates
    if not confirmed and spec.understood.inferred_category_candidates:
        confirmed = list(spec.understood.inferred_category_candidates)

    if not confirmed:
        return spec

    primary = confirmed[0]
    mapping = _mapping_from_candidate(primary, request_text=spec.original_request)
    inferred_summary = " | ".join(candidate_key(item) for item in confirmed)

    understood = spec.understood.model_copy(
        update={
            "inferred_category": inferred_summary,
            "inferred_category_candidates": confirmed,
            "category_level_hint": mapping.mapped_level or "unknown",
        }
    )
    updated = spec.model_copy(update={"understood": understood})
    updated = apply_category_mapping(updated, mapping)

    if len(confirmed) == 1 and mapping.mapped_level == "L3" and mapping.has_sub_l3_qualifiers:
        updated = enrich_understanding_with_related_concept(updated, ai_client=ai_client)

    return updated


def _mapping_from_candidate(
    candidate: InferredCategoryCandidate,
    *,
    request_text: str,
) -> CategoryMappingResult:
    if candidate.l3:
        level = "L3"
    elif candidate.l2:
        level = "L2"
    else:
        level = "L1"

    normalized = request_text.lower()
    return CategoryMappingResult(
        is_relevant=True,
        mapped_level=level,  # type: ignore[arg-type]
        l1=candidate.l1,
        l2=candidate.l2,
        l3=candidate.l3,
        category_path=candidate.category_path or candidate_key(candidate),
        reason=candidate.reason or "用户确认的类目候选",
        confidence=candidate.confidence or ConfidenceLevel.MEDIUM,
        has_sub_l3_qualifiers=level == "L3" and has_sub_l3_qualifiers(normalized),
    )
