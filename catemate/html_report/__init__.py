"""HTML visual report generation from V2 Data Workbook."""

from catemate.html_report.generator import (
    build_html_report_outputs,
    propose_visual_report,
    render_html_report,
)
from catemate.html_report.schemas import VisualReportSpec

__all__ = [
    "VisualReportSpec",
    "build_html_report_outputs",
    "propose_visual_report",
    "render_html_report",
]
