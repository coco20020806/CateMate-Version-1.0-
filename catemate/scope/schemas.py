"""Platform-level scope schemas shared by data modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

from catemate.scope.concept_schemas import RelatedConceptPack

GrainType = Literal["category", "shop", "item"]


@dataclass
class ScopeSpec:
    """External fetch spec: which rows enter a module compute call."""

    grain: GrainType = "category"
    table_id: str = ""
    target_sites: list[str] = field(default_factory=list)
    category_l1: str = ""
    category_l2: str = ""
    category_l3: str = ""
    time_range: str = ""
    scope_label: str = ""
    extra_filters: dict[str, Any] = field(default_factory=dict)
    related_concept_pack: RelatedConceptPack | None = None
    related_min_score: float = 0.55


@dataclass
class ScopedFrame:
    """Filtered rows with original source column names for module compute."""

    data: pd.DataFrame
    scope_label: str
    scope_spec: dict[str, Any] = field(default_factory=dict)
    source_id: str = ""
