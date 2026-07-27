"""Tests for visual report LLM proposal with mocked client."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from openpyxl import Workbook

from catemate.html_report.proposal_generator import propose_visual_report_spec
from catemate.html_report.schemas import VisualReportSpec


def _write_workbook(path: Path) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Data.s_orders.orders_by_site_month")
    ws.append(["grass_region", "grass_month", "orders"])
    ws.append(["BR", "2026-05-01", 54000.0])
    wb.save(path)


def _valid_spec_payload() -> dict:
    return {
        "case_id": "demo",
        "original_question": "orders trend?",
        "report_goal": "Analyze orders",
        "executive_summary": "BR orders 54k.",
        "sections": [
            {
                "section_id": "s_orders",
                "title": "Orders trend",
                "sub_question": "Trend?",
                "narrative": "BR latest 54k.",
                "status": "solved",
                "charts": [
                    {
                        "chart_id": "s_orders_orders_by_site_month",
                        "section_id": "s_orders",
                        "table_id": "orders_by_site_month",
                        "module_id": "monthly_market_trend",
                        "chart_type": "trend",
                        "title": "Orders by site month",
                        "x_field": "grass_month",
                        "y_fields": ["orders"],
                        "series_field": "grass_region",
                        "visible": True,
                        "role": "primary",
                        "binding_source": "llm",
                        "confidence": "high",
                        "notes": [],
                    }
                ],
            }
        ],
        "data_gaps": [],
        "generated_at": "2026-07-17T00:00:00+00:00",
        "spec_status": "draft",
    }


def test_propose_visual_report_spec_with_mock_llm(tmp_path: Path) -> None:
    wb = tmp_path / "data_workbook_demo.xlsx"
    _write_workbook(wb)

    mock_client = MagicMock()
    mock_client.complete_json.return_value = _valid_spec_payload()

    spec = propose_visual_report_spec(
        workbook_path=wb,
        original_question="orders trend?",
        case_id="demo",
        ai_client=mock_client,
    )
    assert isinstance(spec, VisualReportSpec)
    assert spec.case_id == "demo"
    assert spec.sections[0].charts[0].chart_type == "trend"
    assert spec.spec_status == "draft"


def test_propose_falls_back_to_rules_on_llm_failure(tmp_path: Path) -> None:
    wb = tmp_path / "data_workbook_demo.xlsx"
    _write_workbook(wb)

    mock_client = MagicMock()
    mock_client.complete_json.side_effect = RuntimeError("LLM down")

    spec = propose_visual_report_spec(
        workbook_path=wb,
        original_question="orders trend?",
        ai_client=mock_client,
    )
    assert spec.sections
    assert spec.spec_status == "draft"
