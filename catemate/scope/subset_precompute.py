"""Precompute Sub-L3 item scopes before V2 solve loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from catemate.orchestration.module_source_bindings import resolve_table_id
from catemate.scope.executor import execute_scope
from catemate.scope.filters import apply_scope_filters
from catemate.scope.loader import load_table_for_scope
from catemate.scope.scope_cache import MANIFEST_FILENAME, ScopeCache, cache_key
from catemate.scope.sub_l3_artifacts import SubL3ArtifactPaths, export_sub_l3_artifacts
from catemate.scope.schemas import ScopeSpec
from catemate.understanding.schemas import InferredCategoryCandidate, RequirementUnderstandingSpec


@dataclass
class SubsetPrecomputeResult:
    cache: ScopeCache
    cache_dir: Path | None = None
    precomputed: bool = False
    artifact_paths: SubL3ArtifactPaths | None = None


def precompute_subset_scopes(
    spec: RequirementUnderstandingSpec,
    *,
    run_output_dir: Path | None = None,
    processed_data_dir: Path | None = None,
    scope_cache: ScopeCache | None = None,
) -> SubsetPrecomputeResult:
    """Load or build cached item-level frames after if_related filtering."""
    if run_output_dir is not None:
        existing = ScopeCache.load_from_dir(run_output_dir)
        if existing is not None:
            return SubsetPrecomputeResult(cache=existing, cache_dir=existing.disk_dir, precomputed=False)

    understood = spec.understood
    if not understood.sub_l3_concept.is_sub_l3 or understood.related_concept_pack is None:
        return SubsetPrecomputeResult(cache=scope_cache or ScopeCache())

    cache = scope_cache or ScopeCache()
    candidates = _category_candidates(understood)
    pack = understood.related_concept_pack
    min_score = pack.min_score

    for candidate in candidates:
        category_path = (candidate.l1 or "", candidate.l2 or "", candidate.l3 or "")
        table_id = resolve_table_id(
            "monthly_market_trend",
            "item",
            category_path=category_path,
        )
        scope_spec = ScopeSpec(
            grain="item",
            table_id=table_id,
            target_sites=list(understood.target_sites),
            category_l1=candidate.l1 or "",
            category_l2=candidate.l2 or "",
            category_l3=candidate.l3 or "",
            scope_label=_scope_label(understood.target_sites, candidate, pack.display_name),
            related_concept_pack=pack,
            related_min_score=min_score,
        )
        if cache.get(scope_spec) is not None:
            continue

        input_rows = _count_l3_item_rows(scope_spec, processed_data_dir=processed_data_dir)
        frame = execute_scope(
            scope_spec,
            processed_data_dir=processed_data_dir,
            scope_cache=cache,
        )
        key = cache_key(scope_spec)
        if key not in cache.frames:
            cache.put(scope_spec, frame, input_rows=input_rows)
        elif key in cache.entries and input_rows:
            entry = cache.entries[key]
            entry["input_rows"] = input_rows
            output_rows = int(entry.get("output_rows") or 0)
            entry["filter_ratio"] = round(output_rows / input_rows, 4) if input_rows else 1.0

    cache_dir = None
    precomputed = bool(cache.frames)
    artifact_paths = None
    if precomputed and run_output_dir is not None:
        artifact_paths = export_sub_l3_artifacts(spec, run_output_dir, cache)
        cache_dir = artifact_paths.subset_scope_dir if artifact_paths else None

    return SubsetPrecomputeResult(
        cache=cache,
        cache_dir=cache_dir,
        precomputed=precomputed,
        artifact_paths=artifact_paths,
    )


def subset_scope_manifest_exists(run_output_dir: Path) -> bool:
    return (Path(run_output_dir) / "subset_scope" / MANIFEST_FILENAME).exists()


def _category_candidates(understood) -> list[InferredCategoryCandidate]:
    positioning = understood.category_positioning
    if positioning.confirmed_candidates:
        return list(positioning.confirmed_candidates)
    if understood.inferred_category_candidates:
        return list(understood.inferred_category_candidates)
    return [InferredCategoryCandidate()]


def _scope_label(target_sites: list[str], candidate: InferredCategoryCandidate, display_name: str) -> str:
    parts: list[str] = []
    if target_sites:
        parts.append(", ".join(target_sites))
    else:
        parts.append("ALL")
    path = candidate.category_path or " > ".join(
        part for part in [candidate.l1, candidate.l2, candidate.l3] if part
    )
    if path:
        parts.append(path)
    if display_name:
        parts.append(display_name)
    return " / ".join(parts)


def _count_l3_item_rows(scope_spec: ScopeSpec, *, processed_data_dir: Path | None) -> int:
    df, _meta = load_table_for_scope(
        scope_spec.table_id,
        grain=scope_spec.grain,
        category_l1=scope_spec.category_l1,
        category_l2=scope_spec.category_l2,
        category_l3=scope_spec.category_l3,
        processed_data_dir=processed_data_dir,
    )
    filtered = apply_scope_filters(df, scope_spec)
    return len(filtered)
