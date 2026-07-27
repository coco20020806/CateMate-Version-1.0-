"""Tests for conclusion brief generator with mocked LLM."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
from openpyxl import Workbook

from catemate.conclusion_brief.generator import generate_conclusion_brief, normalize_conclusion_brief_raw
from catemate.conclusion_brief.markdown_renderer import render_conclusion_brief_markdown
from catemate.conclusion_brief.schemas import ConclusionBrief


def _write_sample_workbook(path: Path) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Data.orders_by_site_month")
    ws.append(["grass_region", "grass_month", "orders"])
    ws.append(["SG", "2026-05-01", 120.0])
    wb.save(path)


def _valid_brief_payload() -> dict:
    return {
        "original_question": "新加坡智能宠物碗是否有潜力？",
        "report_goal": "分析销量与头部 SKU",
        "executive_summary": "订单量 120，呈温和增长。",
        "overall_assessment": {
            "dimension": "growth_potential",
            "verdict": "有潜力",
            "confidence": "medium",
            "reasoning": "最新月订单 120。",
            "supporting_evidence": ["2026-05 SG 月订单量"],
        },
        "sections": [
            {
                "section_id": "s_orders",
                "title": "销量趋势",
                "sub_question": "订单趋势如何？",
                "direct_answer": "最新月订单 120。",
                "key_numbers": [
                    {
                        "label": "2026-05 SG 月订单量",
                        "value": "120",
                        "unit": "orders",
                        "source_table": "orders_by_site_month",
                        "period": "2026-05",
                    }
                ],
                "qualitative_judgments": [],
            }
        ],
        "cross_cutting_insights": ["市场仍在增长"],
        "data_gaps": [],
        "caveats": [],
        "generated_at": "2026-07-16T00:00:00+00:00",
    }


def test_normalize_conclusion_brief_raw_stringifies_data_gaps() -> None:
    raw = {
        "data_gaps": [
            {"section_id": "s_a", "reason": "缺日度数据"},
            "已有字符串缺口",
        ]
    }
    normalized = normalize_conclusion_brief_raw(raw)
    assert normalized["data_gaps"][0] == "s_a — 缺日度数据"
    assert normalized["data_gaps"][1] == "已有字符串缺口"


def test_generate_conclusion_brief_writes_json_and_md(tmp_path: Path) -> None:
    workbook = tmp_path / "data_workbook_test.xlsx"
    _write_sample_workbook(workbook)
    json_out = tmp_path / "brief.json"
    md_out = tmp_path / "brief.md"

    mock_client = MagicMock()
    mock_client.complete_json.return_value = _valid_brief_payload()

    brief = generate_conclusion_brief(
        workbook_path=workbook,
        original_question="新加坡智能宠物碗是否有潜力？",
        json_output=json_out,
        md_output=md_out,
        ai_client=mock_client,
    )

    assert isinstance(brief, ConclusionBrief)
    assert json_out.exists()
    assert md_out.exists()
    saved = json.loads(json_out.read_text(encoding="utf-8"))
    assert saved["overall_assessment"]["verdict"] == "有潜力"
    md_text = md_out.read_text(encoding="utf-8")
    assert "结论简报" in md_text
    assert "120" in md_text
    mock_client.complete_json.assert_called_once()


def test_render_conclusion_brief_markdown_includes_sections() -> None:
    brief = ConclusionBrief.model_validate(_valid_brief_payload())
    md = render_conclusion_brief_markdown(brief)
    assert "执行摘要" in md
    assert "总体判断" in md
    assert "销量趋势" in md
