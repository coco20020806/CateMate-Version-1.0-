"""Execute Scope: load processed table, filter rows, return ScopedFrame."""

from __future__ import annotations

from pathlib import Path

from catemate.scope.filters import apply_scope_filters
from catemate.scope.loader import load_table_for_scope
from catemate.scope.related import apply_if_related
from catemate.scope.schemas import ScopedFrame, ScopeSpec


def execute_scope(
    spec: ScopeSpec,
    *,
    processed_data_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> ScopedFrame:
    if not spec.table_id:
        raise ValueError("ScopeSpec.table_id is required")

    df, meta = load_table_for_scope(
        spec.table_id,
        grain=spec.grain,
        category_l1=spec.category_l1,
        category_l2=spec.category_l2,
        category_l3=spec.category_l3,
        processed_data_dir=processed_data_dir,
        manifest_path=manifest_path,
    )
    filtered = apply_scope_filters(df, spec)
    if spec.related_concept_pack is not None:
        filtered = apply_if_related(
            filtered,
            spec.related_concept_pack,
            min_score=spec.related_min_score,
        )
    label = spec.scope_label or _default_scope_label(spec)

    scope_spec: dict[str, object] = {
        "grain": spec.grain,
        "table_id": spec.table_id,
        "target_sites": spec.target_sites,
        "category_l1": spec.category_l1,
        "category_l2": spec.category_l2,
        "category_l3": spec.category_l3,
        "time_range": spec.time_range,
    }
    if spec.related_concept_pack is not None:
        scope_spec["related_concept_pack"] = spec.related_concept_pack.model_dump()
        scope_spec["related_min_score"] = spec.related_min_score

    return ScopedFrame(
        data=filtered,
        scope_label=label,
        scope_spec=scope_spec,
        source_id=meta.get("csv_path", ""),
    )


def _default_scope_label(spec: ScopeSpec) -> str:
    parts = []
    if spec.target_sites:
        parts.append("/".join(spec.target_sites))
    for level in (spec.category_l1, spec.category_l2, spec.category_l3):
        if level:
            parts.append(level)
    if spec.time_range:
        parts.append(spec.time_range)
    return " / ".join(parts) or spec.table_id
