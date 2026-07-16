"""Step 1: generate ReportBlueprint from understanding spec."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from catemate.ai.client import CateMateAIClient
from catemate.orchestration.blueprint_validator import validate_blueprint_against_catalog
from catemate.orchestration.module_catalog_builder import (
    build_module_catalog_for_blueprint,
    load_analysis_playbook,
)
from catemate.orchestration.prompt_builder import build_blueprint_messages
from catemate.orchestration.schemas import BlueprintSection, ExpectedShape, ReportBlueprint
from catemate.understanding.schemas import AnalysisIntent, InferredCategoryCandidate, RequirementUnderstandingSpec

_SECTION_BINDINGS: dict[str, tuple[str, str, str]] = {
    "s_market_trend": ("monthly_market_trend", "gmv", "category"),
    "s_orders_trend": ("monthly_market_trend", "orders", "category"),
    "s_top_shop": ("top_shop", "gmv", "shop"),
    "s_daily_cncb": ("daily_cncb_performance", "orders", "category"),
    "s_price_tier": ("price_tier_distribution", "gmv", "category"),
    "s_keywords": ("keywords", "clicks", "category"),
    "s_top_listing": ("top_listing", "gmv", "item"),
    "s_top_sku": ("top_sku_info", "orders", "item"),
}


def build_report_blueprint(
    understanding: RequirementUnderstandingSpec,
    *,
    loop_iteration: int = 1,
    ai_client: CateMateAIClient | None = None,
    processed_data_dir: Path | None = None,
    metadata: dict[str, Any] | None = None,
) -> ReportBlueprint:
    """Generate ReportBlueprint via LLM when available, else deterministic rules."""
    if ai_client is not None:
        try:
            blueprint = _build_with_llm(
                understanding,
                ai_client,
                loop_iteration=loop_iteration,
                processed_data_dir=processed_data_dir,
            )
            if blueprint.sections:
                if metadata is not None:
                    metadata["blueprint_source"] = "llm"
                return blueprint
        except Exception as exc:
            if metadata is not None:
                metadata["blueprint_llm_errors"] = str(exc)
    if metadata is not None:
        metadata["blueprint_source"] = "rules"
    return _build_with_rules(understanding, loop_iteration=loop_iteration)


def _build_with_llm(
    understanding: RequirementUnderstandingSpec,
    ai_client: CateMateAIClient,
    *,
    loop_iteration: int,
    processed_data_dir: Path | None,
) -> ReportBlueprint:
    manifest_path = None
    if processed_data_dir is not None:
        candidate = processed_data_dir / "processed_manifest.yaml"
        if candidate.exists():
            manifest_path = candidate

    catalog = build_module_catalog_for_blueprint(
        include_manifest=True,
        manifest_path=manifest_path,
    )
    playbook = load_analysis_playbook()
    messages = build_blueprint_messages(
        understanding,
        module_catalog=catalog,
        analysis_playbook=playbook,
    )
    payload = ai_client.complete_json(messages)
    normalized = normalize_llm_payload(payload, loop_iteration=loop_iteration, catalog=catalog)
    try:
        blueprint = ReportBlueprint.model_validate(normalized)
    except ValidationError as exc:
        raise ValueError(f"LLM blueprint failed schema validation: {exc}") from exc

    valid, errors = validate_blueprint_against_catalog(blueprint, catalog)
    if not valid:
        raise ValueError("LLM blueprint failed catalog validation: " + "; ".join(errors))
    return blueprint


def normalize_llm_payload(
    payload: dict[str, Any],
    *,
    loop_iteration: int,
    catalog: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    catalog_by_id = {
        str(entry.get("module_id") or "").strip(): entry
        for entry in (catalog or [])
        if str(entry.get("module_id") or "").strip()
    }

    sections_raw = payload.get("sections") or []
    if not isinstance(sections_raw, list):
        sections_raw = []

    sections: list[dict[str, Any]] = []
    for item in sections_raw:
        if not isinstance(item, dict):
            continue
        section_id = str(item.get("section_id") or "").strip()
        if not section_id:
            continue

        expected_shape = item.get("expected_shape") or {}
        if not isinstance(expected_shape, dict):
            expected_shape = {}

        module_id = str(item.get("module_id") or "").strip()
        metric_id = str(item.get("metric_id") or "").strip()
        grain = str(item.get("grain") or "").strip()

        if module_id and not metric_id:
            module_entry = catalog_by_id.get(module_id) or {}
            allowed_metrics = module_entry.get("allowed_metrics") or []
            if allowed_metrics:
                metric_id = str(allowed_metrics[0])

        if not expected_shape.get("metrics") and metric_id:
            expected_shape["metrics"] = [metric_id]

        if not expected_shape.get("grain"):
            module_entry = catalog_by_id.get(module_id) or {}
            output_grains = module_entry.get("output_grains") or []
            if output_grains:
                expected_shape["grain"] = list(output_grains)

        sections.append(
            {
                "section_id": section_id,
                "title": str(item.get("title") or section_id),
                "sub_question": str(item.get("sub_question") or ""),
                "module_id": module_id,
                "metric_id": metric_id,
                "grain": grain,
                "expected_shape": expected_shape,
            }
        )

    goal = str(payload.get("goal") or "").strip()
    return {
        "goal": goal,
        "sections": sections,
        "loop_iteration": loop_iteration,
    }


def _build_with_rules(
    understanding: RequirementUnderstandingSpec,
    *,
    loop_iteration: int = 1,
) -> ReportBlueprint:
    """Deterministic blueprint when LLM is unavailable; mirrors expected report sections."""
    understood = understanding.understood
    goal = understanding.original_request.strip() or understood.target_category_text or "类目分析"
    sections: list[BlueprintSection] = []

    intents = set(understood.analysis_intents or [AnalysisIntent.UNKNOWN])
    sites_label = ", ".join(understood.target_sites) if understood.target_sites else "全部站点"
    confirmed = _confirmed_categories(understood)
    category = understood.inferred_category or understood.target_category_text or "目标类目"
    if len(confirmed) > 1:
        category = " / ".join(
            candidate.category_path or candidate.l3 or candidate.l2 or candidate.l1
            for candidate in confirmed
            if candidate.category_path or candidate.l3 or candidate.l2 or candidate.l1
        ) or category

    if AnalysisIntent.MARKET_TREND in intents or AnalysisIntent.SITE_COMPARISON in intents or not sections:
        title = "市场整体趋势"
        if len(confirmed) > 1:
            title = f"市场整体趋势（{len(confirmed)} 个类目）"
        module_id, metric_id, grain = _SECTION_BINDINGS["s_market_trend"]
        sections.append(
            BlueprintSection(
                section_id="s_market_trend",
                title=title,
                sub_question=f"{category} 在 {sites_label} 的月度 GMV 趋势如何？",
                module_id=module_id,
                metric_id=metric_id,
                grain=grain,
                expected_shape=ExpectedShape(
                    grain=["grass_region", "grass_month"],
                    metrics=["gmv"],
                    presentation="trend_table",
                ),
            )
        )

    if AnalysisIntent.TOP_SHOP in intents:
        module_id, metric_id, grain = _SECTION_BINDINGS["s_top_shop"]
        sections.append(
            BlueprintSection(
                section_id="s_top_shop",
                title="头部店铺对比",
                sub_question=f"{category} 在 {sites_label} 哪些头部 shop 贡献最大？",
                module_id=module_id,
                metric_id=metric_id,
                grain=grain,
                expected_shape=ExpectedShape(
                    grain=["shop_id", "grass_region"],
                    metrics=["gmv"],
                    presentation="ranked_table",
                ),
            )
        )

    if AnalysisIntent.DAILY_PERFORMANCE in intents:
        module_id, metric_id, grain = _SECTION_BINDINGS["s_daily_cncb"]
        sections.append(
            BlueprintSection(
                section_id="s_daily_cncb",
                title="日度 CNCB 表现",
                sub_question=f"{category} 日度 Shopee / CNCB 订单与 GMV 如何？",
                module_id=module_id,
                metric_id=metric_id,
                grain=grain,
                expected_shape=ExpectedShape(
                    grain=["grass_date", "grass_region"],
                    metrics=["orders", "gmv"],
                    presentation="daily_table",
                ),
            )
        )

    if understood.sub_l3_concept.is_sub_l3 or understood.related_concept_pack is not None:
        display_name = (
            understood.sub_l3_concept.display_name
            or (understood.related_concept_pack.display_name if understood.related_concept_pack else "")
            or understood.target_category_text
            or category
        )
        module_id, metric_id, grain = _SECTION_BINDINGS["s_top_sku"]
        sections.append(
            BlueprintSection(
                section_id="s_top_sku",
                title="精准子集 Top SKU",
                sub_question=f"{display_name} 在 {sites_label} 的头部 SKU 有哪些？",
                module_id=module_id,
                metric_id=metric_id,
                grain=grain,
                expected_shape=ExpectedShape(
                    grain=["grass_region", "grass_month", "item_name"],
                    metrics=["orders", "gmv"],
                    presentation="ranked_table",
                ),
            )
        )

    return ReportBlueprint(goal=goal, sections=sections, loop_iteration=loop_iteration)


def _confirmed_categories(understood) -> list[InferredCategoryCandidate]:
    positioning = understood.category_positioning
    if positioning.confirmed_candidates:
        return list(positioning.confirmed_candidates)
    if understood.inferred_category_candidates:
        return list(understood.inferred_category_candidates)
    return []
