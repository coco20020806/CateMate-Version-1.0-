"""Schemas for Sub-L3 related concept packs used by if_related filtering."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RelatedConceptPack(BaseModel):
    """LLM-generated or fallback concept pack for item-level relevance filtering."""

    concept_id: str
    display_name: str
    parent_l3: str = ""
    scope_note: str = ""
    smart_signals: list[str] = Field(default_factory=list)
    pet_context: list[str] = Field(default_factory=list)
    boost_terms: list[str] = Field(default_factory=list)
    exclude_terms: list[str] = Field(default_factory=list)
    min_score: float = 0.55
