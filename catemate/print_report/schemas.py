"""Schemas for print_vertical_report (consulting-style print HTML)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PageLayout = Literal["cover", "toc", "insight", "evidence", "actions"]
CardKind = Literal["summary", "opportunity", "risk", "decision"]
ChartKind = Literal["hbar", "column", "trend_svg", "none"]
MetricKind = Literal["money", "orders", "percent", "label", "other"]


class FuzzyMetric(BaseModel):
    label: str
    display: str
    kind: MetricKind = "other"
    raw_suppressed: bool = True


class InsightCard(BaseModel):
    kind: CardKind = "summary"
    headline: str
    body: str = ""
    fuzzy_metrics: list[FuzzyMetric] = Field(default_factory=list)


class TableCell(BaseModel):
    text: str
    tone: str = ""  # up / down / neutral


class EvidenceTable(BaseModel):
    headers: list[str] = Field(default_factory=list)
    rows: list[list[TableCell]] = Field(default_factory=list)


class CssChartSeries(BaseModel):
    label: str
    relative: float  # 0-100 bar width / height share
    display: str = ""  # fuzzy label for axis/caption


class CssChart(BaseModel):
    kind: ChartKind = "hbar"
    title: str = ""
    series: list[CssChartSeries] = Field(default_factory=list)
    caption: str = ""


class EvidenceBlock(BaseModel):
    conclusion: str
    chart: CssChart | None = None
    table: EvidenceTable | None = None
    notes: list[str] = Field(default_factory=list)


class NextAction(BaseModel):
    action: str
    owner_hint: str = "品类 / 运营"
    priority: Literal["high", "medium", "low"] = "medium"


class PrintPage(BaseModel):
    page_id: str
    so_what_title: str
    layout: PageLayout
    cards: list[InsightCard] = Field(default_factory=list)
    blocks: list[EvidenceBlock] = Field(default_factory=list)
    toc_items: list[str] = Field(default_factory=list)
    body_paragraphs: list[str] = Field(default_factory=list)


class PrintTheme(BaseModel):
    brand: str = "#EE4D2D"
    brand_dark: str = "#C23A1F"
    up: str = "#15803d"
    down: str = "#b91c1c"
    surface: str = "#ffffff"
    muted: str = "#6b7280"


class PrintReportDoc(BaseModel):
    case_id: str = ""
    title: str = ""
    subtitle: str = ""
    generated_at: str = ""
    theme: PrintTheme = Field(default_factory=PrintTheme)
    executive_summary: str = ""
    pages: list[PrintPage] = Field(default_factory=list)
    next_actions: list[NextAction] = Field(default_factory=list)
    delivery_notes: list[str] = Field(default_factory=list)
    fuzzy_applied: bool = True
    disclaimer: str = (
        "本报告数值已模糊化（百分比区间 / 金额与单量量级桶），不适合做精确对账；"
        "对账请使用 Visual Report 或 Data Workbook。"
    )
