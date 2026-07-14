"""Validate config/data_modules/*.yaml against Data Module Schema v2 rules."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODULES_DIR = ROOT / "config" / "data_modules"
MANIFEST = ROOT / "CateMate_processeddata" / "processed_manifest.yaml"

REQUIRED = [
    "schema_version",
    "module_id",
    "module_name",
    "status",
    "business_purpose",
    "lineage",
    "fields",
    "default_charts",
    "limitations",
]

EXPECTED_ACTIVE = {
    "rm_monthly_category_performance",
    "dashboard_history_market_trend",
    "dashboard_daily_cncb_performance",
    "dashboard_price_tier_distribution",
    "dashboard_top_shop",
    "dashboard_keywords",
    "dashboard_top_listing",
}


def main() -> int:
    errors: list[str] = []
    parsed = 0
    active: list[str] = []
    deprecated: list[str] = []

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    manifest_ids = {
        t["table_id"] for t in manifest.get("tables", []) if isinstance(t, dict) and t.get("table_id")
    }

    for path in sorted(MODULES_DIR.glob("*.yaml")):
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            parsed += 1
        except Exception as exc:
            errors.append(f"PARSE {path.name}: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"NOT_DICT {path.name}")
            continue

        status = str(payload.get("status", "active")).lower()
        if status == "deprecated":
            deprecated.append(str(payload.get("module_id", path.stem)))
            continue
        if path.name.startswith("_"):
            continue

        module_id = str(payload.get("module_id", path.stem))
        active.append(module_id)

        for key in REQUIRED:
            if key not in payload:
                errors.append(f"MISSING {path.name}: {key}")

        business_purpose = payload.get("business_purpose")
        if not isinstance(business_purpose, dict) or not business_purpose.get("description"):
            errors.append(f"MISSING {path.name}: business_purpose.description")

        lineage = payload.get("lineage") or {}
        source_tables = lineage.get("source_tables") or []
        if not source_tables:
            errors.append(f"MISSING {path.name}: lineage.source_tables")

        fields = payload.get("fields") or {}
        if not fields.get("dimensions"):
            errors.append(f"MISSING {path.name}: fields.dimensions")
        if not fields.get("metrics"):
            errors.append(f"MISSING {path.name}: fields.metrics")

        default_charts = payload.get("default_charts") or []
        if not default_charts:
            errors.append(f"MISSING {path.name}: default_charts (empty)")

        for item in source_tables:
            if isinstance(item, dict):
                table_id = item.get("table_id")
                if table_id and table_id not in manifest_ids:
                    errors.append(f"UNKNOWN_TABLE {path.name}: {table_id}")

    print("=== YAML parse ===")
    print(f"parsed files: {parsed}")
    print(f"active modules ({len(active)}): {active}")
    print(f"deprecated modules: {deprecated}")

    if set(active) != EXPECTED_ACTIVE:
        errors.append(f"active module set mismatch: expected {sorted(EXPECTED_ACTIVE)}, got {sorted(active)}")

    if errors:
        print("ERRORS:")
        for err in errors:
            print(" -", err)
        return 1
    print("YAML validation: OK")

    from catemate.planning.context_loader import _summarize_data_module, load_data_module_configs

    mods = load_data_module_configs(MODULES_DIR, active_only=True)
    ids = [m.get("module_id") for m in mods]
    print("=== context_loader ===")
    print(f"active loaded: {len(mods)}")
    print("module_ids:", ids)

    if "sph_category_dashboard_deck" in ids:
        errors.append("deprecated module sph_category_dashboard_deck in active list")

    summaries = [_summarize_data_module(m) for m in mods]
    if not all(s.get("default_charts") for s in summaries):
        errors.append("some active module summaries missing default_charts")

    all_with_deprecated = load_data_module_configs(MODULES_DIR, active_only=False)
    dep_in_all = [
        m.get("module_id")
        for m in all_with_deprecated
        if str(m.get("status", "")).lower() == "deprecated"
    ]
    print(f"deprecated in full load (active_only=False): {dep_in_all}")

    if errors:
        print("SMOKE ERRORS:")
        for err in errors:
            print(" -", err)
        return 1

    print("context_loader smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
