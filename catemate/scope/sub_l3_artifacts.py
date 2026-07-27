"""Export Sub-L3 if_related filtered item data and filter rules as run artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from catemate.scope.related import (
    BOOST_SCORE,
    ITEM_NAME_COLUMN,
    PET_CONTEXT_SCORE,
    SMART_SCORE_CAP,
    SMART_SCORE_PER_HIT,
    STRONG_SMART_BONUS,
    TRANSLATION_COLUMN,
)
from catemate.scope.scope_cache import ScopeCache
from catemate.understanding.schemas import RequirementUnderstandingSpec

FILTER_SPEC_FILENAME = "sub_l3_filter_spec.json"
FILTER_RULES_MD_FILENAME = "sub_l3_filter_rules.md"
SPEC_VERSION = "sub_l3_filter_spec_v1"


@dataclass
class SubL3ArtifactPaths:
    subset_scope_dir: Path
    filter_spec_path: Path
    filter_rules_path: Path


def export_sub_l3_artifacts(
    spec: RequirementUnderstandingSpec,
    run_dir: Path,
    cache: ScopeCache,
) -> SubL3ArtifactPaths | None:
    """Persist CSV/parquet cache plus filter spec and markdown rules under subset_scope/."""
    if not cache.frames:
        return None

    cache_dir = cache.save_to_dir(run_dir)
    filter_spec = build_filter_spec(spec, cache, case_id=spec.case_id)
    filter_spec_path = cache_dir / FILTER_SPEC_FILENAME
    filter_spec_path.write_text(
        json.dumps(filter_spec, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    filter_rules_path = cache_dir / FILTER_RULES_MD_FILENAME
    filter_rules_path.write_text(render_filter_rules_markdown(filter_spec), encoding="utf-8")
    return SubL3ArtifactPaths(
        subset_scope_dir=cache_dir,
        filter_spec_path=filter_spec_path,
        filter_rules_path=filter_rules_path,
    )


def build_filter_spec(
    spec: RequirementUnderstandingSpec,
    cache: ScopeCache,
    *,
    case_id: str = "",
) -> dict[str, Any]:
    understood = spec.understood
    pack = understood.related_concept_pack
    if pack is None:
        raise ValueError("related_concept_pack is required for filter spec export")

    positioning = understood.category_positioning
    if positioning.confirmed_candidates:
        confirmed = [item.model_dump(mode="json") for item in positioning.confirmed_candidates]
    else:
        confirmed = [item.model_dump(mode="json") for item in understood.inferred_category_candidates]

    data_slices: list[dict[str, Any]] = []
    for entry in cache.entries.values():
        data_slices.append(
            {
                "csv_file": entry.get("csv_file") or "",
                "parquet_file": entry.get("parquet_file") or "",
                "input_rows_l3": entry.get("input_rows"),
                "output_rows_matched": entry.get("output_rows"),
                "filter_ratio": entry.get("filter_ratio"),
                "source_id": entry.get("source_id") or "",
                "category_l1": entry.get("category_l1") or "",
                "category_l2": entry.get("category_l2") or "",
                "category_l3": entry.get("category_l3") or "",
                "target_sites": entry.get("target_sites") or [],
            }
        )

    return {
        "spec_version": SPEC_VERSION,
        "case_id": case_id or spec.case_id,
        "original_request": spec.original_request,
        "sub_l3_concept": understood.sub_l3_concept.model_dump(mode="json"),
        "related_concept_pack": pack.model_dump(mode="json"),
        "category_scope": {
            "target_sites": list(understood.target_sites),
            "confirmed_categories": confirmed,
        },
        "filter_algorithm": {
            "name": "if_related",
            "module": "catemate.scope.related",
            "search_columns": [ITEM_NAME_COLUMN, TRANSLATION_COLUMN],
            "pass_condition": "related_score >= min_score AND NOT excluded",
            "scoring_constants": {
                "smart_score_per_hit": SMART_SCORE_PER_HIT,
                "smart_score_cap": SMART_SCORE_CAP,
                "strong_smart_bonus": STRONG_SMART_BONUS,
                "pet_context_score": PET_CONTEXT_SCORE,
                "boost_score": BOOST_SCORE,
            },
        },
        "data_slices": data_slices,
    }


def render_filter_rules_markdown(spec_dict: dict[str, Any]) -> str:
    pack = spec_dict.get("related_concept_pack") or {}
    sub_l3 = spec_dict.get("sub_l3_concept") or {}
    category_scope = spec_dict.get("category_scope") or {}
    algorithm = spec_dict.get("filter_algorithm") or {}
    constants = algorithm.get("scoring_constants") or {}

    lines: list[str] = [
        "# Sub-L3 if_related 筛选规则",
        "",
        f"**需求原文**：{spec_dict.get('original_request') or '—'}",
        "",
        f"**Sub-L3 概念**：{sub_l3.get('display_name') or pack.get('display_name') or '—'}",
        f"**父级 L3**：{sub_l3.get('parent_l3') or pack.get('parent_l3') or '—'}",
        "",
        "## 宽定义（scope_note）",
        "",
        pack.get("scope_note") or "—",
        "",
        f"**通过阈值 min_score**：{pack.get('min_score', '—')}",
        "",
        "## 通过逻辑",
        "",
        "- 在 `item_name` + `translation` 上检索",
        "- 命中 exclude_terms → 分数归零，不通过",
        "- 必须同时命中 smart_signals 与 pet_context",
        f"- `related_score >= {pack.get('min_score')}` 则保留",
        "",
        "## 打分常量",
        "",
        "| 常量 | 值 |",
        "| --- | --- |",
    ]
    for key, value in constants.items():
        lines.append(f"| `{key}` | {value} |")

    lines.extend(["", "## 词表", ""])
    for label, field_name in (
        ("smart_signals", "smart_signals"),
        ("pet_context", "pet_context"),
        ("boost_terms", "boost_terms"),
        ("exclude_terms", "exclude_terms"),
    ):
        terms = pack.get(field_name) or []
        lines.append(f"### {label}")
        lines.append("")
        if terms:
            for term in terms:
                lines.append(f"- `{term}`")
        else:
            lines.append("- （无）")
        lines.append("")

    sites = category_scope.get("target_sites") or []
    lines.extend(
        [
            "## 类目与站点范围",
            "",
            f"- **目标站点**：{', '.join(sites) if sites else 'ALL（全部站点）'}",
            "",
        ]
    )
    for item in category_scope.get("confirmed_categories") or []:
        path = item.get("category_path") or " > ".join(
            part for part in [item.get("l1"), item.get("l2"), item.get("l3")] if part
        )
        lines.append(f"- `{path}`")

    lines.extend(["", "## 数据切片统计", ""])
    lines.append("| CSV 文件 | L3 输入行 | 匹配行 | 比例 |")
    lines.append("| --- | ---: | ---: | ---: |")
    for slice_item in spec_dict.get("data_slices") or []:
        csv_name = slice_item.get("csv_file") or "—"
        input_rows = slice_item.get("input_rows_l3") or "—"
        output_rows = slice_item.get("output_rows_matched") or "—"
        ratio = slice_item.get("filter_ratio")
        ratio_text = f"{ratio:.4f}" if isinstance(ratio, (int, float)) else "—"
        lines.append(f"| `{csv_name}` | {input_rows} | {output_rows} | {ratio_text} |")

    lines.append("")
    return "\n".join(lines)
