"""Tests for html_report schemas."""

from __future__ import annotations

from catemate.html_report.schemas import ChartBinding, VisualReportSpec


def test_chart_binding_defaults() -> None:
    binding = ChartBinding(
        chart_id="c1",
        section_id="s1",
        table_id="orders_by_site_month",
        chart_type="trend",
        title="Orders trend",
    )
    assert binding.visible is True
    assert binding.role == "primary"
    assert binding.confidence == "medium"


def test_visual_report_spec_roundtrip() -> None:
    spec = VisualReportSpec(
        case_id="demo",
        original_question="Q?",
        report_goal="Goal",
        executive_summary="Summary",
        spec_status="draft",
    )
    payload = spec.model_dump(mode="json")
    restored = VisualReportSpec.model_validate(payload)
    assert restored.case_id == "demo"
    assert restored.spec_status == "draft"
