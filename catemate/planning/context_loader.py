"""Load and compress planning context from YAML configs and processed manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from catemate.core.paths import CONFIG_DIR, PROCESSED_DATA_DIR


DEFAULT_MANIFEST_PATH = PROCESSED_DATA_DIR / "processed_manifest.yaml"
DEFAULT_DATA_MODULES_DIR = CONFIG_DIR / "data_modules"


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on runtime env.
        raise RuntimeError(
            "PyYAML is required to read planning YAML files. "
            "Please install it with `pip install PyYAML`."
        ) from exc

    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _should_include_data_module(path: Path, payload: dict[str, Any], *, active_only: bool) -> bool:
    """Skip templates and optionally deprecated modules."""
    if path.name.startswith("_"):
        return False
    if active_only and str(payload.get("status", "active")).lower() == "deprecated":
        return False
    return True


def load_case_config(path: Path) -> dict[str, Any]:
    """Load a case config YAML as a plain dict (compressed later by builder)."""
    payload = _load_yaml(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid case config format in {path}: top-level must be a mapping")
    return payload


def load_processed_manifest(path: Path) -> dict[str, Any]:
    """Load processed_manifest.yaml."""
    payload = _load_yaml(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid processed manifest format in {path}: top-level must be a mapping")
    return payload


def load_data_module_configs(
    directory: Path,
    *,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """Load data module configs under a directory.

    By default skips ``_template.yaml`` and modules with ``status: deprecated``.
    """
    if not directory.exists():
        raise FileNotFoundError(f"Data modules directory not found: {directory}")

    modules: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        payload = _load_yaml(path)
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid data module config format in {path}: top-level must be a mapping")
        if not _should_include_data_module(path, payload, active_only=active_only):
            continue
        module = dict(payload)
        module["_config_path"] = str(path)
        modules.append(module)
    return modules


def build_planning_context(
    case_config_path: Path,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    data_modules_dir: Path = DEFAULT_DATA_MODULES_DIR,
) -> dict[str, Any]:
    """Build a compressed planning context for the AI planner."""
    case_config = load_case_config(case_config_path)
    manifesto = load_processed_manifest(manifest_path)
    modules = load_data_module_configs(data_modules_dir, active_only=True)

    return {
        "case_config_path": str(case_config_path),
        "manifest_path": str(manifest_path),
        "data_modules_dir": str(data_modules_dir),
        "case_config": _summarize_case_config(case_config),
        "processed_tables": _summarize_manifest_tables(manifesto),
        "data_modules": [_summarize_data_module(module) for module in modules],
        "manifest_meta": {
            "generated_at": manifesto.get("generated_at", ""),
            "table_count": len(manifesto.get("tables") or []),
        },
    }


def _summarize_case_config(case_config: dict[str, Any]) -> dict[str, Any]:
    keep_keys = [
        "case_id",
        "project_name",
        "original_request",
        "target_category_text",
        "business_background",
        "delivery_audience",
        "delivery_format",
        "target_sites",
        "time_range",
        "category_keywords",
        "source_file_keywords",
        "required_sheets",
        "required_fields",
    ]
    summary = {key: case_config.get(key) for key in keep_keys if key in case_config}

    analysis_plan = case_config.get("analysis_plan") or []
    if isinstance(analysis_plan, list) and analysis_plan:
        summary["analysis_plan_summary"] = [
            {
                "analysis_block": row.get("analysis_block", ""),
                "question": row.get("question", ""),
                "support_status": row.get("support_status", ""),
            }
            for row in analysis_plan[:12]
            if isinstance(row, dict)
        ]

    chart_requirements = case_config.get("chart_requirements") or []
    if isinstance(chart_requirements, list) and chart_requirements:
        summary["chart_requirements_summary"] = [
            {
                "chart_page": row.get("chart_page", ""),
                "required_table": row.get("required_table", ""),
                "status": row.get("status", ""),
                "chart_type": row.get("chart_type"),
            }
            for row in chart_requirements[:12]
            if isinstance(row, dict)
        ]
    return summary


def _summarize_manifest_tables(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    tables = manifest.get("tables") or []
    summaries: list[dict[str, Any]] = []
    for table in tables:
        if not isinstance(table, dict):
            continue
        summaries.append(
            {
                "table_id": table.get("table_id", ""),
                "description": table.get("description", ""),
                "source_workbook_name": table.get("source_workbook_name", ""),
                "source_sheet": table.get("source_sheet", ""),
                "columns": table.get("columns") or [],
                "row_count": table.get("row_count"),
                "important_fields": table.get("important_fields") or [],
                "update_mode": table.get("update_mode", ""),
            }
        )
    return summaries


def _extract_table_ids(module: dict[str, Any]) -> list[str]:
    """Collect table_id from v1 source_tables or v2 lineage.source_tables."""
    table_ids: list[str] = []
    for container_key in ("lineage", None):
        if container_key:
            container = module.get(container_key) or {}
            source_tables = container.get("source_tables") or []
        else:
            source_tables = module.get("source_tables") or []
        for item in source_tables:
            if isinstance(item, dict) and item.get("table_id"):
                table_id = str(item["table_id"])
                if table_id not in table_ids:
                    table_ids.append(table_id)
    return table_ids


def _summarize_default_charts(module: dict[str, Any]) -> list[dict[str, Any]]:
    charts = module.get("default_charts") or []
    summaries: list[dict[str, Any]] = []
    for chart in charts:
        if not isinstance(chart, dict):
            continue
        summaries.append(
            {
                "chart_intent": chart.get("chart_intent", ""),
                "default_chart_type": chart.get("default_chart_type", ""),
                "title_template": chart.get("title_template", ""),
                "x_axis": chart.get("x_axis"),
                "y_axis": chart.get("y_axis") or [],
                "series": chart.get("series"),
                "sort_rule": chart.get("sort_rule", ""),
                "top_n": chart.get("top_n"),
            }
        )
    return summaries


def _summarize_data_module(module: dict[str, Any]) -> dict[str, Any]:
    business_purpose = module.get("business_purpose") or {}
    if not isinstance(business_purpose, dict):
        business_purpose = {}

    planning_hints = module.get("planning_hints") or {}
    if not isinstance(planning_hints, dict):
        planning_hints = {}

    typical_questions = business_purpose.get("typical_questions") or []
    if not typical_questions:
        typical_questions = (
            module.get("supported_questions")
            or module.get("answerable_questions")
            or []
        )

    default_charts = _summarize_default_charts(module)
    chart_types = module.get("chart_types") or []
    if not chart_types and default_charts:
        chart_types = list(
            dict.fromkeys(
                str(chart.get("default_chart_type", ""))
                for chart in default_charts
                if chart.get("default_chart_type")
            )
        )

    description = (
        business_purpose.get("description")
        or module.get("description")
        or module.get("purpose")
        or ""
    )

    summary: dict[str, Any] = {
        "module_id": module.get("module_id", ""),
        "module_name": module.get("module_name") or module.get("name") or "",
        "schema_version": module.get("schema_version", ""),
        "module_type": module.get("module_type", ""),
        "status": module.get("status", "active"),
        "description": description,
        "typical_questions": typical_questions,
        "answerable_questions": typical_questions,
        "source_tables": _extract_table_ids(module),
        "default_charts": default_charts,
        "chart_types": chart_types,
        "limitations": module.get("limitations") or [],
        "filter_dimensions": module.get("filter_dimensions") or [],
    }

    use_when = planning_hints.get("use_when") or []
    avoid_when = planning_hints.get("avoid_when") or []
    explicit_triggers = planning_hints.get("explicit_triggers") or []
    if use_when:
        summary["use_when"] = use_when
    if avoid_when:
        summary["avoid_when"] = avoid_when
    if explicit_triggers:
        summary["explicit_triggers"] = explicit_triggers

    preferred_over = planning_hints.get("preferred_over") or []
    if preferred_over:
        summary["preferred_over"] = preferred_over

    return summary
