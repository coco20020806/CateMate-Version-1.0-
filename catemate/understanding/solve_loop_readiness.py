"""Prepare RequirementUnderstandingSpec before V2 solve loop."""

from __future__ import annotations

from catemate.ai.client import CateMateAIClient
from catemate.understanding.category_confirmation import (
    finalize_after_category_confirmation,
    is_category_confirmation_complete,
)
from catemate.understanding.concept_pack_generator import enrich_understanding_with_related_concept
from catemate.understanding.schemas import RequirementUnderstandingSpec
from catemate.understanding.sub_l3_detector import should_generate_concept_pack


def ensure_understanding_ready_for_solve_loop(
    spec: RequirementUnderstandingSpec,
    ai_client: CateMateAIClient | None = None,
) -> RequirementUnderstandingSpec:
    """Finalize category mapping and attach related concept pack when needed."""
    updated = spec
    if is_category_confirmation_complete(updated):
        updated = finalize_after_category_confirmation(updated, ai_client=ai_client)

    if should_generate_concept_pack(updated) and updated.understood.related_concept_pack is None:
        updated = enrich_understanding_with_related_concept(updated, ai_client=ai_client)

    return updated
