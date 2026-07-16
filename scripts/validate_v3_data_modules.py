"""Validate data_modules/<id>/contract.yaml (V3 Python modules) status policy."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_MODULES_DIR = ROOT / "data_modules"
EXPECTED_ACTIVE = {"monthly_market_trend", "top_sku_info"}
POLICY_PATH = ROOT / "config" / "output_grain_policy.yaml"


def main() -> int:
    errors: list[str] = []
    active: list[str] = []
    other: list[str] = []

    policy_enabled = _load_policy_enabled_modules()
    if set(policy_enabled) != EXPECTED_ACTIVE:
        errors.append(
            f"POLICY_MISMATCH expected={sorted(EXPECTED_ACTIVE)} "
            f"got={sorted(policy_enabled)} from output_grain_policy.yaml"
        )

    for contract_path in sorted(DATA_MODULES_DIR.glob("*/contract.yaml")):
        payload = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            errors.append(f"NOT_DICT {contract_path}")
            continue

        module_id = str(payload.get("module_id") or contract_path.parent.name).strip()
        status = str(payload.get("status", "active")).lower()

        if status == "active":
            active.append(module_id)
            compute_py = contract_path.parent / "compute.py"
            if not compute_py.exists():
                errors.append(f"MISSING compute.py for active module {module_id}")
            test_dir = ROOT / "tests" / "data_modules" / module_id
            if not test_dir.exists():
                errors.append(f"MISSING tests/data_modules/{module_id}/ for active module {module_id}")
        else:
            other.append(f"{module_id}:{status}")

    if set(active) != EXPECTED_ACTIVE:
        errors.append(
            f"ACTIVE_MISMATCH expected={sorted(EXPECTED_ACTIVE)} got={sorted(active)}"
        )

    if errors:
        for item in errors:
            print(f"ERROR {item}")
        return 1

    print(f"OK active={sorted(active)}")
    print(f"OK non_active={other}")
    return 0


def _load_policy_enabled_modules() -> set[str]:
    if not POLICY_PATH.exists():
        return set()
    payload = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return set()
    modules = payload.get("enabled_v2_modules") or []
    return {str(item).strip() for item in modules if str(item).strip()}


if __name__ == "__main__":
    raise SystemExit(main())
