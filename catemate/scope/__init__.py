"""Scope layer: filter processed tables into module-ready ScopedFrames."""

from .concept_schemas import RelatedConceptPack
from .executor import execute_scope
from .related import apply_if_related
from .schemas import ScopedFrame, ScopeSpec
from .scope_cache import ScopeCache

__all__ = [
    "RelatedConceptPack",
    "ScopedFrame",
    "ScopeCache",
    "ScopeSpec",
    "apply_if_related",
    "execute_scope",
]
