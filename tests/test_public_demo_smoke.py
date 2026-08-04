from __future__ import annotations

import json

from scripts.build_synthetic_demo import build


def test_synthetic_demo_creates_auditable_deliverables(tmp_path):
    build(tmp_path)
    assert (tmp_path / "data_workbook_synthetic_demo.xlsx").exists()
    assert (tmp_path / "gaps.md").exists()
    assert (tmp_path / "visual_report.html").exists()
    manifest = json.loads((tmp_path / "pipeline_manifest_synthetic_demo.json").read_text())
    assert manifest["demo"] is True
    assert manifest["active_module"] == "monthly_market_trend"
