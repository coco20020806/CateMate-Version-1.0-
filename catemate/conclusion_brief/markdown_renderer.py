"""Render ConclusionBrief to Markdown."""

from __future__ import annotations

from catemate.conclusion_brief.schemas import ConclusionBrief, ConclusionBriefSection, QualitativeJudgment


def _render_judgment(j: QualitativeJudgment) -> str:
    evidence = "、".join(j.supporting_evidence) if j.supporting_evidence else "—"
    return (
        f"- **{j.dimension}** → {j.verdict}（置信度：{j.confidence}）\n"
        f"  - 依据：{j.reasoning}\n"
        f"  - 支撑数据：{evidence}"
    )


def _render_section(section: ConclusionBriefSection) -> str:
    lines = [
        f"### {section.title}",
        f"**子问题**：{section.sub_question}",
        "",
        section.direct_answer,
        "",
    ]
    if section.key_numbers:
        lines.append("**关键数字**")
        for num in section.key_numbers:
            period = f"（{num.period}）" if num.period else ""
            unit = f" {num.unit}" if num.unit else ""
            source = f" — 来源 `{num.source_table}`" if num.source_table else ""
            lines.append(f"- {num.label}{period}：**{num.value}**{unit}{source}")
        lines.append("")
    if section.qualitative_judgments:
        lines.append("**定性判断**")
        for judgment in section.qualitative_judgments:
            lines.append(_render_judgment(judgment))
        lines.append("")
    return "\n".join(lines)


def render_conclusion_brief_markdown(brief: ConclusionBrief) -> str:
    lines = [
        "# 结论简报",
        "",
        f"**原始问题**：{brief.original_question}",
        "",
        f"**报告目标**：{brief.report_goal}",
        "",
        "## 执行摘要",
        "",
        brief.executive_summary,
        "",
        "## 总体判断",
        "",
        _render_judgment(brief.overall_assessment),
        "",
    ]

    if brief.sections:
        lines.extend(["## 分章节结论", ""])
        for section in brief.sections:
            lines.append(_render_section(section))

    if brief.cross_cutting_insights:
        lines.extend(["## 综合洞察", ""])
        for insight in brief.cross_cutting_insights:
            lines.append(f"- {insight}")
        lines.append("")

    if brief.data_gaps:
        lines.extend(["## 数据缺口", ""])
        for gap in brief.data_gaps:
            lines.append(f"- {gap}")
        lines.append("")

    if brief.caveats:
        lines.extend(["## 注意事项", ""])
        for caveat in brief.caveats:
            lines.append(f"- {caveat}")
        lines.append("")

    if brief.generated_at:
        lines.append(f"---\n*生成时间：{brief.generated_at}*")

    return "\n".join(lines)
