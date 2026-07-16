"""Scope + compute pilot script for category grain."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.scope.executor import execute_scope
from catemate.scope.schemas import ScopeSpec
from data_modules.monthly_market_trend import ComputeParams, compute, transform


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Scope + monthly_market_trend compute pilot.")
    parser.add_argument("--table-id", default="dashboard_history")
    parser.add_argument("--metric-id", default="gmv", choices=["gmv", "orders", "aov"])
    parser.add_argument("--sites", default="", help="Comma-separated sites, e.g. SG,VN")
    parser.add_argument("--category-l2", default="")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "outputs" / "scope_pilot")
    args = parser.parse_args()

    sites = [s.strip() for s in args.sites.split(",") if s.strip()]
    spec = ScopeSpec(
        grain="category",
        table_id=args.table_id,
        target_sites=sites,
        category_l2=args.category_l2,
        scope_label=f"{','.join(sites) or 'ALL'} / {args.category_l2 or 'ALL'}",
    )
    frame = execute_scope(spec)
    primary = compute(ComputeParams(metric_id=args.metric_id), frame)
    derived = transform(primary)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "scope_label": frame.scope_label,
        "input_rows": len(frame.data),
        "primary_tables": list(primary.keys()),
        "derived_tables": list(derived.keys()),
    }
    out_path = args.output_dir / f"scope_compute_{args.metric_id}.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
