"""Compose PrintReportDoc from confirmed VisualReportSpec + workbook (+ optional Brief)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from catemate.conclusion_brief.schemas import ConclusionBrief
from catemate.html_report.data_loader import (
    load_workbook_table_entries,
    resolve_table_for_binding,
)
from catemate.html_report.schemas import ChartBinding, VisualReportSpec
from catemate.print_report.fuzzy import (
    format_price_range_label,
    fuzzy_metric,
    infer_metric_kind,
    relative_share,
)
from catemate.print_report.schemas import (
    CssChart,
    CssChartSeries,
    EvidenceBlock,
    EvidenceTable,
    InsightCard,
    NextAction,
    PrintPage,
    PrintReportDoc,
    TableCell,
)

SITE_FIELDS = ("grass_region", "region", "site")
TIME_FIELDS = ("grass_month", "month", "year_month", "grass_date", "date")
DELIVERY_NOTES = [
    "打开 HTML 后，文字区域可直接在网页中编辑微调。",
    "导出 PDF：浏览器 Ctrl+P / Command+P → Save as PDF，建议 A4 横向（Landscape）。",
    "若需转成 PPT：可先导出 PDF 再用 PDF→PPT 工具；仅在内容已脱敏或非敏感时，才建议使用公开在线转换网站。",
]


def compose_print_report_doc(
    *,
    spec: VisualReportSpec,
    workbook_path: Path,
    brief: ConclusionBrief | None = None,
) -> PrintReportDoc:
    if spec.spec_status != "confirmed":
        raise ValueError("VisualReportSpec must be confirmed before generating print report.")

    entries = load_workbook_table_entries(workbook_path)
    brief_by_section = {
        section.section_id: section for section in (brief.sections if brief else [])
    }
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    title = spec.report_goal or spec.original_question or f"{spec.case_id} 类目深度分析报告"
    executive = (brief.executive_summary if brief and brief.executive_summary else "") or spec.executive_summary

    pages: list[PrintPage] = []
    pages.append(
        PrintPage(
            page_id="cover",
            so_what_title=f"{title} | Category Deep-Dive",
            layout="cover",
            body_paragraphs=[
                f"Case: {spec.case_id or '—'}",
                f"Generated: {generated_at}",
                "数值已模糊化 · Print Vertical Report",
            ],
        )
    )

    toc_items = ["执行摘要 / Executive Summary"]
    for section in spec.sections:
        toc_items.append(section.title or section.section_id)
    toc_items.append("核心总结与下一步 / Next Actions")
    pages.append(
        PrintPage(
            page_id="toc",
            so_what_title="目录 | Table of Contents",
            layout="toc",
            toc_items=toc_items,
        )
    )

    summary_cards = _build_summary_cards(spec, entries, brief)
    pages.append(
        PrintPage(
            page_id="executive",
            so_what_title="执行摘要 | Where to play & why it matters",
            layout="insight",
            body_paragraphs=[executive] if executive else ["本轮已确认图表结构；以下为模糊化后的关键判断。"],
            cards=summary_cards,
        )
    )

    for section in spec.sections:
        brief_section = brief_by_section.get(section.section_id)
        so_what = _so_what_title(section.title, brief_section.direct_answer if brief_section else section.narrative)
        narrative = (
            (brief_section.direct_answer if brief_section else "")
            or section.narrative
            or f"{section.title}：先结论后证据（数值已模糊化）。"
        )
        blocks: list[EvidenceBlock] = []
        for chart in section.charts:
            if not chart.visible:
                continue
            block = _evidence_from_chart(chart, entries)
            if block is not None:
                blocks.append(block)
        if brief_section and brief_section.key_numbers:
            metric_cards = [
                fuzzy_metric(item.label, item.value)
                for item in brief_section.key_numbers[:6]
            ]
            blocks.insert(
                0,
                EvidenceBlock(
                    conclusion=narrative,
                    notes=[f"{m.label}: {m.display}" for m in metric_cards],
                ),
            )
        elif not blocks:
            blocks.append(EvidenceBlock(conclusion=narrative))

        # Split into pages of at most 2 evidence blocks to avoid overflow.
        chunk_size = 2
        for index in range(0, max(len(blocks), 1), chunk_size):
            chunk = blocks[index : index + chunk_size]
            suffix = "" if index == 0 else f" · {index // chunk_size + 1}"
            pages.append(
                PrintPage(
                    page_id=f"{section.section_id}_{index // chunk_size + 1}",
                    so_what_title=f"{so_what}{suffix}",
                    layout="evidence",
                    body_paragraphs=[narrative] if index == 0 else [],
                    blocks=chunk or [EvidenceBlock(conclusion=narrative)],
                )
            )

    insights = list(brief.cross_cutting_insights) if brief else []
    if not insights:
        insights = [
            "优先加大主力市场投放与供给，机会市场以测款+内容验证增速。",
            "价格带与站点结构差异决定选品与定价策略，避免一刀切。",
            "热销 SKU / 店铺信号用于补货与跟卖优先级，而非直接复制链接运营。",
        ]
    next_actions = _default_next_actions(spec, brief)
    pages.append(
        PrintPage(
            page_id="actions",
            so_what_title="核心总结与下一步 | Decisions & Next Actions",
            layout="actions",
            body_paragraphs=insights[:6],
            cards=[
                InsightCard(kind="decision", headline="决策焦点", body=insights[0] if insights else ""),
            ],
        )
    )

    return PrintReportDoc(
        case_id=spec.case_id,
        title=title,
        subtitle=spec.original_question,
        generated_at=generated_at,
        executive_summary=executive,
        pages=pages,
        next_actions=next_actions,
        delivery_notes=list(DELIVERY_NOTES),
        fuzzy_applied=True,
    )


def _so_what_title(module_title: str, answer: str) -> str:
    module = (module_title or "分析模块").strip()
    short = (answer or "").strip().replace("\n", " ")
    if short:
        short = short[:48] + ("…" if len(short) > 48 else "")
        return f"{module} | {short}"
    return f"{module} | Key takeaway"


def _build_summary_cards(
    spec: VisualReportSpec,
    entries,
    brief: ConclusionBrief | None,
) -> list[InsightCard]:
    cards: list[InsightCard] = []
    if brief and brief.overall_assessment.verdict:
        cards.append(
            InsightCard(
                kind="summary",
                headline="总体判断",
                body=brief.overall_assessment.verdict,
            )
        )

    site_totals = _aggregate_site_metric(spec, entries)
    if site_totals:
        ranked = sorted(site_totals.items(), key=lambda item: item[1], reverse=True)
        leaders = ranked[:3]
        cards.append(
            InsightCard(
                kind="summary",
                headline="主力市场（体量）",
                body="、".join(name for name, _ in leaders) or "—",
                fuzzy_metrics=[
                    fuzzy_metric(f"{name} ADG/GMV 量级", value, kind="money")
                    for name, value in leaders
                ],
            )
        )
        # Opportunity proxy: mid-pack sites (not top1) with non-trivial volume.
        opportunity = [item for item in ranked[1:4]]
        if opportunity:
            cards.append(
                InsightCard(
                    kind="opportunity",
                    headline="机会市场（次主力 / 跟进验证）",
                    body="、".join(name for name, _ in opportunity),
                    fuzzy_metrics=[
                        fuzzy_metric(f"{name} 量级", value, kind="money")
                        for name, value in opportunity
                    ],
                )
            )

    cards.append(
        InsightCard(
            kind="risk",
            headline="使用边界",
            body="汇报稿已模糊化金额/单量/占比；精确核对请回到 Visual Report 或 workbook。",
        )
    )
    return cards[:4]


def _aggregate_site_metric(spec: VisualReportSpec, entries) -> dict[str, float]:
    totals: dict[str, float] = {}
    for section in spec.sections:
        for chart in section.charts:
            if not chart.visible:
                continue
            entry = resolve_table_for_binding(
                entries,
                table_id=chart.table_id,
                run_id=chart.run_id,
                section_id=chart.section_id,
                sheet_name=chart.sheet_name,
            )
            if entry is None or entry.df.empty:
                continue
            df = entry.df
            site_field = next((c for c in SITE_FIELDS if c in df.columns), None)
            y_field = next((y for y in chart.y_fields if y in df.columns), None)
            if site_field is None or y_field is None:
                continue
            if infer_metric_kind(y_field) == "percent":
                continue
            work = df.copy()
            work[y_field] = pd.to_numeric(work[y_field], errors="coerce")
            grouped = work.groupby(site_field, dropna=False)[y_field].sum(min_count=1)
            for site, value in grouped.items():
                if pd.isna(value):
                    continue
                key = str(site)
                totals[key] = totals.get(key, 0.0) + float(value)
            if totals:
                return totals
    return totals


def _evidence_from_chart(chart: ChartBinding, entries) -> EvidenceBlock | None:
    entry = resolve_table_for_binding(
        entries,
        table_id=chart.table_id,
        run_id=chart.run_id,
        section_id=chart.section_id,
        sheet_name=chart.sheet_name,
    )
    if entry is None or entry.df.empty:
        return EvidenceBlock(
            conclusion=f"{chart.title}：对应表未找到或为空，已跳过证据图。",
        )

    df = entry.df
    if chart.chart_type == "trend":
        return _trend_block(chart, df)
    if chart.chart_type in {"bar", "share"}:
        return _bar_share_block(chart, df)
    if chart.chart_type == "table":
        return _table_block(chart, df)
    return EvidenceBlock(conclusion=f"{chart.title}：以文字结论呈现（chart_type={chart.chart_type}）。")


def _trend_block(chart: ChartBinding, df: pd.DataFrame) -> EvidenceBlock:
    x_field = chart.x_field if chart.x_field in df.columns else next(
        (c for c in TIME_FIELDS if c in df.columns), None
    )
    y_field = next((y for y in chart.y_fields if y in df.columns), None)
    if x_field is None or y_field is None:
        return EvidenceBlock(conclusion=f"{chart.title}：缺少时间或指标字段。")

    work = df.copy()
    work[y_field] = pd.to_numeric(work[y_field], errors="coerce")
    grouped = work.groupby(x_field, dropna=False)[y_field].sum(min_count=1).reset_index()
    grouped = grouped.sort_values(x_field)
    values = [float(v) if pd.notna(v) else 0.0 for v in grouped[y_field].tolist()]
    labels = [_format_month_label(v) for v in grouped[x_field].tolist()]
    shares = relative_share(values)
    series = [
        CssChartSeries(label=label, relative=rel, display="相对水位")
        for label, rel in zip(labels, shares)
    ]
    # Highlight inflection as month with max relative jump.
    inflection = ""
    if len(values) >= 2:
        deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
        best = max(range(len(deltas)), key=lambda i: abs(deltas[i]))
        direction = "上升" if deltas[best] >= 0 else "下降"
        inflection = f"关键拐点约在 {labels[best + 1]}（相对前月{direction}）。"

    return EvidenceBlock(
        conclusion=f"{chart.title}：展示相对月度走势（不贴每月绝对值）。{inflection}",
        chart=CssChart(
            kind="trend_svg",
            title=chart.title,
            series=series[:12],
            caption="纵轴为相对份额，非真实金额。",
        ),
    )


def _bar_share_block(chart: ChartBinding, df: pd.DataFrame) -> EvidenceBlock:
    dim = chart.x_field if chart.x_field in df.columns else next(
        (c for c in list(SITE_FIELDS) + ["Price_Range_USD", "level3_global_be_category"] if c in df.columns),
        None,
    )
    y_field = next((y for y in chart.y_fields if y in df.columns), None)
    if dim is None or y_field is None:
        return EvidenceBlock(conclusion=f"{chart.title}：缺少维度或指标。")

    work = df.copy()
    work[y_field] = pd.to_numeric(work[y_field], errors="coerce")
    grouped = work.groupby(dim, dropna=False)[y_field].sum(min_count=1).reset_index()
    grouped = grouped.sort_values(y_field, ascending=False).head(chart.top_n or 8)
    values = [float(v) if pd.notna(v) else 0.0 for v in grouped[y_field].tolist()]
    labels = [format_price_range_label(v) if dim == "Price_Range_USD" else str(v) for v in grouped[dim].tolist()]
    shares = relative_share(values)
    kind = infer_metric_kind(y_field)
    series = [
        CssChartSeries(
            label=label,
            relative=rel,
            display=fuzzy_metric(y_field, value, kind=kind).display if kind != "percent" else fuzzy_metric(y_field, rel / 100.0, kind="percent").display,
        )
        for label, rel, value in zip(labels, shares, values)
    ]
    return EvidenceBlock(
        conclusion=f"{chart.title}：头部结构如下（展示模糊量级 / 区间占比）。",
        chart=CssChart(
            kind="hbar",
            title=chart.title,
            series=series,
            caption="条长表示相对份额；右侧为模糊标签。",
        ),
    )


def _table_block(chart: ChartBinding, df: pd.DataFrame) -> EvidenceBlock:
    preferred = [
        c
        for c in ["grass_region", "item_name", "rank", "gmv_usd", "orders", "item_price_usd"]
        if c in df.columns
    ]
    cols = preferred or list(df.columns[:5])
    sample = df[cols].head(8)
    headers = [str(c) for c in cols]
    rows: list[list[TableCell]] = []
    for _, row in sample.iterrows():
        cells: list[TableCell] = []
        for col in cols:
            value = row.get(col)
            if col in {"gmv_usd", "orders", "item_price_usd"} or infer_metric_kind(col) in {"money", "orders", "percent"}:
                cells.append(TableCell(text=fuzzy_metric(col, value).display))
            elif col == "Price_Range_USD":
                cells.append(TableCell(text=format_price_range_label(value)))
            else:
                text = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)
                if col == "item_name" and len(text) > 60:
                    text = text[:57] + "..."
                cells.append(TableCell(text=text))
        rows.append(cells)
    return EvidenceBlock(
        conclusion=f"{chart.title}：Top 样本（指标列已模糊化）。",
        table=EvidenceTable(headers=headers, rows=rows),
    )


def _format_month_label(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if len(text) >= 7 and text[4] == "-":
        return text[:7]
    return text


def _default_next_actions(spec: VisualReportSpec, brief: ConclusionBrief | None) -> list[NextAction]:
    actions = [
        NextAction(
            action="确认主力站点供给与广告预算是否匹配体量判断（量级口径）。",
            owner_hint="品类运营",
            priority="high",
        ),
        NextAction(
            action="对机会站点做 1–2 周测款 + 内容验证，观察相对增速而非绝对值。",
            owner_hint="站点运营",
            priority="high",
        ),
        NextAction(
            action="对照热销 SKU / 价格带结构，调整跟卖与定价带，避免跨站一刀切。",
            owner_hint="选品",
            priority="medium",
        ),
    ]
    if brief and brief.data_gaps:
        actions.append(
            NextAction(
                action=f"补齐数据缺口：{brief.data_gaps[0]}",
                owner_hint="数据分析",
                priority="medium",
            )
        )
    elif spec.data_gaps:
        actions.append(
            NextAction(
                action=f"复核数据缺口：{spec.data_gaps[0]}",
                owner_hint="数据分析",
                priority="low",
            )
        )
    return actions[:5]
