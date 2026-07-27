"""Render VisualReportSpec to standalone HTML."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from catemate.html_report.chart_builders import build_chart_figure
from catemate.html_report.data_loader import (
    load_workbook_table_entries,
    repair_chart_binding,
    resolve_table_for_binding,
)
from catemate.html_report.schemas import ChartBinding, VisualReportSection, VisualReportSpec


def _templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def _figure_to_html(fig) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False)


def render_section_charts(
    section: VisualReportSection,
    entries,
) -> list[dict[str, str]]:
    rendered: list[dict[str, str]] = []
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
        if entry is None:
            rendered.append(
                {
                    "role": chart.role,
                    "html": f"<p><em>Chart {chart.chart_id} failed: table not found ({chart.table_id})</em></p>",
                }
            )
            continue
        binding: ChartBinding = repair_chart_binding(chart, entry.df)
        try:
            fig = build_chart_figure(entry.df, binding)
            rendered.append(
                {
                    "role": chart.role,
                    "html": _figure_to_html(fig),
                }
            )
        except Exception as exc:
            rendered.append(
                {
                    "role": chart.role,
                    "html": f"<p><em>Chart {chart.chart_id} failed: {exc}</em></p>",
                }
            )
    return rendered


def render_html_report(
    *,
    spec: VisualReportSpec,
    workbook_path: Path,
    output_path: Path | None = None,
) -> Path:
    if spec.spec_status != "confirmed":
        raise ValueError("VisualReportSpec must be confirmed before rendering HTML.")

    entries = load_workbook_table_entries(workbook_path)
    env = Environment(
        loader=FileSystemLoader(str(_templates_dir())),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.j2")

    sections_payload: list[dict] = []
    for section in spec.sections:
        charts = render_section_charts(section, entries)
        sections_payload.append(
            {
                "title": section.title,
                "sub_question": section.sub_question,
                "narrative": section.narrative,
                "status": section.status,
                "charts": charts,
            }
        )

    title = spec.report_goal or spec.original_question or "CateMate Visual Report"
    html = template.render(
        title=title,
        report_goal=spec.report_goal,
        executive_summary=spec.executive_summary,
        sections=sections_payload,
        data_gaps=spec.data_gaps,
    )

    if output_path is None:
        output_path = workbook_path.with_name(workbook_path.stem.replace("data_workbook", "html_report") + ".html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
