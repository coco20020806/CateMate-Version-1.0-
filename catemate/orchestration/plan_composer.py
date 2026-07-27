"""Step 2: map ReportBlueprint sections to executable AnalysisPlan runs."""

from __future__ import annotations

from catemate.orchestration.derived_tables import comparison_table_id
from catemate.orchestration.module_source_bindings import resolve_table_id
from catemate.orchestration.schemas import AnalysisPlan, PlanRun, ReportBlueprint, ScopeKind
from catemate.understanding.schemas import InferredCategoryCandidate, RequirementUnderstandingSpec

_SECTION_MODULE_MAP = {
    "s_market_trend": ("monthly_market_trend", "gmv", "category"),
    "s_orders_trend": ("monthly_market_trend", "orders", "category"),
    "s_top_sku": ("top_sku_info", "orders", "item"),
}

_SCOPE_ORDER = {"subset": 0, "parent_l3": 1, "standard": 2, "comparison": 3}


def compose_analysis_plan(
    blueprint: ReportBlueprint,
    understanding: RequirementUnderstandingSpec,
) -> AnalysisPlan:
    understood = understanding.understood
    sites = understood.target_sites
    candidates = _confirmed_candidates(understood)
    runs: list[PlanRun] = []
    run_index = 0

    for cat_index, candidate in enumerate(candidates, start=1):
        category_l1 = candidate.l1 or ""
        category_l2 = candidate.l2 or ""
        category_l3 = candidate.l3 or ""
        category_path = (category_l1, category_l2, category_l3)
        category_label = (
            candidate.category_path
            or category_l3
            or category_l2
            or category_l1
            or understood.target_category_text
            or "ALL"
        )

        for section in blueprint.sections:
            run_index += 1
            if section.module_id and section.metric_id and section.grain:
                module_id = section.module_id
                metric = section.metric_id
            elif mapping := _SECTION_MODULE_MAP.get(section.section_id):
                module_id, metric, _ = mapping
            else:
                metric = section.expected_shape.metrics[0] if section.expected_shape.metrics else "gmv"
                module_id = "monthly_market_trend"

            scope_kind = _resolve_scope_kind(section, understanding, module_id)
            grain, table_id, related_pack, related_min_score = _resolve_scope_binding(
                scope_kind,
                module_id,
                understanding,
                candidate,
                category_path,
                metric,
            )
            source_kind = "computed" if scope_kind == "comparison" else "rawdata"

            scope_parts = [
                ", ".join(sites) if sites else "ALL",
                category_label,
            ]
            sub_label = _subset_display_label(understood)
            if scope_kind == "subset" and sub_label:
                scope_parts.append(sub_label)
            scope_label = " / ".join(part for part in scope_parts if part)

            suffix = f"_c{cat_index}" if len(candidates) > 1 else ""
            runs.append(
                PlanRun(
                    run_id=f"r{run_index}{suffix}",
                    section_id=section.section_id,
                    grain=grain,  # type: ignore[arg-type]
                    module_id=module_id,
                    metric_id=metric,
                    scope_label=scope_label,
                    required_catalog=f"{grain}/{table_id}" if table_id else f"{grain}/derived",
                    table_id=table_id,
                    target_sites=sites,
                    category_l1=category_l1,
                    category_l2=category_l2,
                    category_l3=category_l3,
                    related_concept_pack=related_pack,
                    related_min_score=related_min_score,
                    is_sub_category=scope_kind == "subset",
                    scope_kind=scope_kind,
                    source_kind=source_kind,
                )
            )

    _validate_plan_runs(runs)
    runs.sort(key=lambda r: (_SCOPE_ORDER.get(r.scope_kind, 2), r.metric_id, r.run_id))
    return AnalysisPlan(goal=blueprint.goal, runs=runs, loop_iteration=blueprint.loop_iteration)


def _confirmed_candidates(understood) -> list[InferredCategoryCandidate]:
    positioning = understood.category_positioning
    if positioning.confirmed_candidates:
        return list(positioning.confirmed_candidates)
    if understood.inferred_category_candidates:
        return list(understood.inferred_category_candidates)
    return [InferredCategoryCandidate()]


def _section_text(section) -> str:
    return " ".join([section.section_id, section.title, section.sub_question]).lower()


def _is_parent_section(section) -> bool:
    text = _section_text(section)
    return "parent" in text or "父级" in section.title or "父级" in section.sub_question


def _is_comparison_section(section) -> bool:
    text = _section_text(section)
    markers = (" vs ", "_vs_", "share", "份额", "占比", "比例")
    return any(marker in text for marker in markers)


def _resolve_scope_kind(section, understanding: RequirementUnderstandingSpec, module_id: str) -> ScopeKind:
    understood = understanding.understood
    if _is_comparison_section(section):
        return "comparison"
    if _is_parent_section(section):
        return "parent_l3"
    if understood.sub_l3_concept.is_sub_l3 and understood.related_concept_pack is not None:
        if module_id in {"monthly_market_trend", "top_sku_info"}:
            return "subset"
    return "standard"


def _resolve_scope_binding(
    scope_kind: ScopeKind,
    module_id: str,
    understanding: RequirementUnderstandingSpec,
    candidate: InferredCategoryCandidate,
    category_path: tuple[str, str, str],
    metric: str,
) -> tuple[str, str, dict | None, float]:
    understood = understanding.understood
    related_min_score = 0.55
    if scope_kind == "subset":
        if understood.related_concept_pack is None:
            raise ValueError("subset scope requires related_concept_pack")
        grain = "item"
        table_id = resolve_table_id(
            module_id,
            grain,
            category_path=category_path,
        )
        return grain, table_id, understood.related_concept_pack.model_dump(), related_min_score

    if scope_kind == "parent_l3":
        grain = "category"
        table_id = resolve_table_id(module_id, grain)
        return grain, table_id, None, related_min_score

    if scope_kind == "comparison":
        grain = "category"
        table_id = comparison_table_id(metric)
        return grain, table_id, None, related_min_score

    grain = "item" if module_id == "top_sku_info" else "category"
    table_id = resolve_table_id(
        module_id,
        grain,
        category_path=category_path if grain == "item" else None,
    )
    related_pack = None
    if (
        understood.related_concept_pack is not None
        and module_id == "top_sku_info"
        and understood.sub_l3_concept.is_sub_l3
    ):
        related_pack = understood.related_concept_pack.model_dump()
        related_min_score = understood.related_concept_pack.min_score
    return grain, table_id, related_pack, related_min_score


def _subset_display_label(understood) -> str:
    return (
        understood.sub_l3_concept.display_name
        or (understood.related_concept_pack.display_name if understood.related_concept_pack else "")
        or understood.target_category_text
        or ""
    )


def _validate_plan_runs(runs: list[PlanRun]) -> None:
    for run in runs:
        if run.scope_kind == "subset":
            if run.grain != "item":
                raise ValueError(f"{run.run_id}: subset scope requires grain=item")
            if run.related_concept_pack is None:
                raise ValueError(f"{run.run_id}: subset scope requires related_concept_pack")
            if not run.is_sub_category:
                raise ValueError(f"{run.run_id}: subset scope requires is_sub_category=True")
        if run.scope_kind == "parent_l3":
            if run.grain != "category":
                raise ValueError(f"{run.run_id}: parent_l3 scope requires grain=category")
            if run.related_concept_pack is not None:
                raise ValueError(f"{run.run_id}: parent_l3 scope must not attach related_concept_pack")
            if run.is_sub_category:
                raise ValueError(f"{run.run_id}: parent_l3 scope requires is_sub_category=False")
        if run.scope_kind == "comparison":
            metric_id = run.metric_id
            has_subset = any(
                item.scope_kind == "subset" and item.metric_id == metric_id for item in runs
            )
            has_parent = any(
                item.scope_kind == "parent_l3" and item.metric_id == metric_id for item in runs
            )
            if not has_subset or not has_parent:
                raise ValueError(
                    f"{run.run_id}: comparison scope requires subset and parent_l3 runs "
                    f"for metric_id={metric_id}"
                )
