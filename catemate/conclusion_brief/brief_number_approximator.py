"""Apply number approximation rules across a ConclusionBrief."""

from __future__ import annotations

from catemate.conclusion_brief.number_format import approximate_number, approximate_text_numbers
from catemate.conclusion_brief.schemas import (
    ConclusionBrief,
    ConclusionBriefSection,
    EvidenceNumber,
    QualitativeJudgment,
)


def _approximate_evidence_number(item: EvidenceNumber) -> EvidenceNumber:
    return item.model_copy(
        update={"value": approximate_number(item.value, unit=item.unit)}
    )


def _approximate_judgment(judgment: QualitativeJudgment) -> QualitativeJudgment:
    return judgment.model_copy(
        update={"reasoning": approximate_text_numbers(judgment.reasoning)}
    )


def _approximate_section(section: ConclusionBriefSection) -> ConclusionBriefSection:
    return section.model_copy(
        update={
            "direct_answer": approximate_text_numbers(section.direct_answer),
            "key_numbers": [_approximate_evidence_number(n) for n in section.key_numbers],
            "qualitative_judgments": [
                _approximate_judgment(j) for j in section.qualitative_judgments
            ],
        }
    )


def apply_number_approximation(brief: ConclusionBrief) -> ConclusionBrief:
    """Return a copy of the brief with all display numbers approximately formatted."""
    return brief.model_copy(
        update={
            "executive_summary": approximate_text_numbers(brief.executive_summary),
            "overall_assessment": _approximate_judgment(brief.overall_assessment),
            "sections": [_approximate_section(s) for s in brief.sections],
            "cross_cutting_insights": [
                approximate_text_numbers(item) for item in brief.cross_cutting_insights
            ],
            "data_gaps": [approximate_text_numbers(item) for item in brief.data_gaps],
            "caveats": [approximate_text_numbers(item) for item in brief.caveats],
        }
    )
