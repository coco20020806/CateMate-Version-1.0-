"""Render PrintReportDoc to print_vertical_report HTML."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from catemate.print_report.charts_css import render_css_chart
from catemate.print_report.schemas import PrintReportDoc


def _templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def render_print_report_html(doc: PrintReportDoc) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_templates_dir())),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals["render_css_chart"] = render_css_chart
    template = env.get_template("print_vertical_report.html.j2")
    return template.render(doc=doc)


def write_print_report_html(doc: PrintReportDoc, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = render_print_report_html(doc)
    output_path.write_text(html, encoding="utf-8")
    return output_path
