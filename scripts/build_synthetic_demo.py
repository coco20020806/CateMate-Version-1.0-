"""Build safe, deterministic demo deliverables from the committed synthetic data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def build(output_dir: Path) -> None:
    source = ROOT / "examples" / "processed_data" / "source_tables" / "dashboard_history.csv"
    data = pd.read_csv(source)
    data["grass_month"] = pd.to_datetime(data["grass_month"])
    trend = data.groupby(["grass_region", "grass_month"], as_index=False)[["gmv_usd", "orders"]].sum()
    output_dir.mkdir(parents=True, exist_ok=True)
    workbook = output_dir / "data_workbook_synthetic_demo.xlsx"
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        pd.DataFrame([{"title": "CateMate Synthetic Demo", "status": "solved"}]).to_excel(writer, sheet_name="Plan", index=False)
        trend.to_excel(writer, sheet_name="Data.monthly_market_trend", index=False)
        pd.DataFrame([{"gap": "Price-tier and keyword modules are not active in this public demo."}]).to_excel(writer, sheet_name="Gaps", index=False)
    manifest = {
        "demo": True,
        "data_source": "examples/processed_data/source_tables/dashboard_history.csv",
        "scope": {"site": "SG", "category": "Stationery"},
        "active_module": "monthly_market_trend",
        "deliverables": [workbook.name, "gaps.md", "visual_report.html"],
    }
    (output_dir / "pipeline_manifest_synthetic_demo.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "gaps.md").write_text("# Gaps\n\nPrice-tier and keyword analysis are intentionally not active in the public demo.\n", encoding="utf-8")
    (output_dir / "visual_report.html").write_text("<h1>CateMate Synthetic Demo</h1><p>Deterministic monthly trend output generated from synthetic data.</p>", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "synthetic_demo")
    args = parser.parse_args()
    build(args.output_dir)
    print(f"Synthetic demo created: {args.output_dir}")


if __name__ == "__main__":
    main()
