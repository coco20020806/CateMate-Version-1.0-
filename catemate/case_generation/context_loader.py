"""Shared helpers for natural-language case config generation scripts."""

from __future__ import annotations

import re
from datetime import datetime
import csv
from pathlib import Path
from typing import Any

from catemate.schemas.category_requirement import CategoryAnalysisCaseConfig


def load_request_text(request_text: str, request_file: Path | None) -> str:
    """Load request text from CLI text or a file path."""
    if request_file is not None:
        if not request_file.exists():
            raise FileNotFoundError(f"request-file not found: {request_file}")
        text = request_file.read_text(encoding="utf-8").strip()
    else:
        text = request_text.strip()

    if not text:
        raise ValueError("Please provide --request-text or --request-file with non-empty content.")
    return text


def load_reference_case_summaries(directory: Path) -> list[dict[str, Any]]:
    """Load compressed summaries from config/cases/*.yaml."""
    if not directory.exists():
        raise FileNotFoundError(f"Reference cases directory not found: {directory}")
    summaries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        payload = load_yaml(path)
        if not isinstance(payload, dict):
            continue
        summaries.append(
            {
                "case_id": payload.get("case_id", ""),
                "project_name": payload.get("project_name", ""),
                "original_request": payload.get("original_request", ""),
                "target_category_text": payload.get("target_category_text", ""),
                "target_sites": payload.get("target_sites") or [],
                "category_keywords": payload.get("category_keywords") or [],
                "analysis_plan": payload.get("analysis_plan") or [],
                "chart_requirements": payload.get("chart_requirements") or [],
            }
        )
    return summaries


def load_data_module_summaries(directory: Path) -> list[dict[str, Any]]:
    """Load compressed summaries from config/data_modules/*.yaml (active modules only)."""
    if not directory.exists():
        raise FileNotFoundError(f"Data modules directory not found: {directory}")
    summaries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        payload = load_yaml(path)
        if not isinstance(payload, dict):
            continue
        if str(payload.get("status", "active")).lower() == "deprecated":
            continue

        business_purpose = payload.get("business_purpose") or {}
        if not isinstance(business_purpose, dict):
            business_purpose = {}

        table_ids: list[str] = []
        for container in (payload.get("lineage") or {}, payload):
            source_tables = container.get("source_tables") or []
            for item in source_tables:
                if isinstance(item, dict) and item.get("table_id"):
                    tid = str(item["table_id"])
                    if tid not in table_ids:
                        table_ids.append(tid)
                elif isinstance(item, str) and item not in table_ids:
                    table_ids.append(item)

        default_charts = payload.get("default_charts") or []
        chart_types = payload.get("chart_types") or []
        if not chart_types and default_charts:
            chart_types = list(
                dict.fromkeys(
                    str(c.get("default_chart_type", ""))
                    for c in default_charts
                    if isinstance(c, dict) and c.get("default_chart_type")
                )
            )

        typical_questions = business_purpose.get("typical_questions") or []
        if not typical_questions:
            typical_questions = (
                payload.get("answerable_questions")
                or payload.get("supported_questions")
                or []
            )

        summaries.append(
            {
                "module_id": payload.get("module_id", ""),
                "module_name": payload.get("module_name", ""),
                "schema_version": payload.get("schema_version", ""),
                "description": business_purpose.get("description")
                or payload.get("description")
                or payload.get("purpose")
                or "",
                "answerable_questions": typical_questions,
                "source_tables": table_ids,
                "default_charts": default_charts,
                "chart_types": chart_types,
                "limitations": payload.get("limitations") or [],
            }
        )
    return summaries


def load_yaml(path: Path) -> Any:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to read YAML files. Please install it with `pip install PyYAML`."
        ) from exc

    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_case_config_yaml(case_config: CategoryAnalysisCaseConfig, output_path: Path) -> Path:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to write YAML files. Please install it with `pip install PyYAML`."
        ) from exc

    payload = case_config.model_dump(by_alias=True, mode="json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    return output_path


def slug_or_empty(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace(" ", "_")
    normalized = re.sub(r"[^a-z0-9_]", "_", normalized)
    return re.sub(r"_+", "_", normalized).strip("_")


def safe_slug(value: str, timestamp: str | None = None) -> str:
    normalized = slug_or_empty(value)
    if normalized:
        return normalized
    stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"generated_case_{stamp}"


def fallback_case_id(project_name: str, timestamp: str | None = None) -> str:
    stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    base = slug_or_empty(project_name)
    if base:
        return f"generated_{base}_{stamp}"
    return f"generated_case_{stamp}"


def ensure_case_id(
    case_config: CategoryAnalysisCaseConfig,
    timestamp: str | None = None,
) -> CategoryAnalysisCaseConfig:
    """Fill empty case_id without rewriting an existing one."""
    if case_config.case_id.strip():
        return case_config
    generated_id = fallback_case_id(case_config.project_name, timestamp=timestamp)
    return case_config.model_copy(update={"case_id": generated_id})


def load_category_tree_l3_candidates(lookup_csv_path: Path) -> list[dict[str, str]]:
    """Load full L1/L2/L3 candidates from category lookup CSV."""
    if not lookup_csv_path.exists():
        raise FileNotFoundError(f"Category tree lookup CSV not found: {lookup_csv_path}")

    candidates: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    with lookup_csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            l1 = str(row.get("l1") or "").strip()
            l2 = str(row.get("l2") or "").strip()
            l3 = str(row.get("l3") or "").strip()
            if not l3:
                continue
            key = (l1, l2, l3)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            category_path = " > ".join(part for part in [l1, l2, l3] if part)
            candidates.append(
                {
                    "l1": l1,
                    "l2": l2,
                    "l3": l3,
                    "category_path": category_path,
                }
            )
    return candidates
