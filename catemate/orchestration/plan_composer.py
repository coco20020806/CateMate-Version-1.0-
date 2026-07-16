"""Step 2: map ReportBlueprint sections to executable AnalysisPlan runs."""

from __future__ import annotations

from catemate.orchestration.module_source_bindings import resolve_table_id
from catemate.orchestration.schemas import AnalysisPlan, PlanRun, ReportBlueprint
from catemate.understanding.schemas import InferredCategoryCandidate, RequirementUnderstandingSpec

_SECTION_MODULE_MAP = {
    "s_market_trend": ("monthly_market_trend", "gmv", "category"),
    "s_orders_trend": ("monthly_market_trend", "orders", "category"),
    "s_top_shop": ("top_shop", "gmv", "shop"),
    "s_daily_cncb": ("daily_cncb_performance", "orders", "category"),
    "s_price_tier": ("price_tier_distribution", "gmv", "category"),
    "s_keywords": ("keywords", "clicks", "category"),
    "s_top_listing": ("top_listing", "gmv", "item"),
    "s_top_sku": ("top_sku_info", "orders", "item"),
}


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
                grain = section.grain  # type: ignore[assignment]
            elif mapping := _SECTION_MODULE_MAP.get(section.section_id):
                module_id, metric, grain = mapping
            else:
                metric = section.expected_shape.metrics[0] if section.expected_shape.metrics else "gmv"
                module_id = "monthly_market_trend"
                grain = "category"

            table_id = resolve_table_id(
                module_id,
                grain,
                category_path=category_path if grain == "item" else None,
            )

            scope_parts = [
                ", ".join(sites) if sites else "ALL",
                category_label,
            ]
            if section.section_id == "s_top_sku":
                sub_label = (
                    understood.sub_l3_concept.display_name
                    or (
                        understood.related_concept_pack.display_name
                        if understood.related_concept_pack
                        else ""
                    )
                )
                if sub_label:
                    scope_parts.append(sub_label)
            scope_label = " / ".join(part for part in scope_parts if part)

            related_pack = None
            related_min_score = 0.55
            if _should_attach_related_pack(understood, candidate):
                related_pack = understood.related_concept_pack.model_dump()
                related_min_score = understood.related_concept_pack.min_score

            suffix = f"_c{cat_index}" if len(candidates) > 1 else ""
            runs.append(
                PlanRun(
                    run_id=f"r{run_index}{suffix}",
                    section_id=section.section_id,
                    grain=grain,  # type: ignore[arg-type]
                    module_id=module_id,
                    metric_id=metric,
                    scope_label=scope_label,
                    required_catalog=f"{grain}/{table_id}",
                    table_id=table_id,
                    target_sites=sites,
                    category_l1=category_l1,
                    category_l2=category_l2,
                    category_l3=category_l3,
                    related_concept_pack=related_pack,
                    related_min_score=related_min_score,
                )
            )

    return AnalysisPlan(goal=blueprint.goal, runs=runs, loop_iteration=blueprint.loop_iteration)


def _confirmed_candidates(understood) -> list[InferredCategoryCandidate]:
    positioning = understood.category_positioning
    if positioning.confirmed_candidates:
        return list(positioning.confirmed_candidates)
    if understood.inferred_category_candidates:
        return list(understood.inferred_category_candidates)
    return [InferredCategoryCandidate()]


def _should_attach_related_pack(understood, candidate: InferredCategoryCandidate) -> bool:
    if understood.related_concept_pack is None:
        return False
    if not understood.sub_l3_concept.is_sub_l3:
        return False
    parent_l3 = understood.sub_l3_concept.parent_l3.strip()
    if parent_l3 and candidate.l3 and candidate.l3 != parent_l3:
        return False
    return True
