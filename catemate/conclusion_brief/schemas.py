"""Pydantic schemas for LLM-generated conclusion briefs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["high", "medium", "low"]


class EvidenceNumber(BaseModel):
    label: str
    value: str
    unit: str = ""
    source_table: str = ""
    period: str = ""


class QualitativeJudgment(BaseModel):
    dimension: str
    verdict: str
    confidence: ConfidenceLevel = "medium"
    reasoning: str
    supporting_evidence: list[str] = Field(default_factory=list)


class ConclusionBriefSection(BaseModel):
    section_id: str
    title: str
    sub_question: str
    direct_answer: str
    key_numbers: list[EvidenceNumber] = Field(default_factory=list)
    qualitative_judgments: list[QualitativeJudgment] = Field(default_factory=list)


class ConclusionBrief(BaseModel):
    original_question: str
    report_goal: str
    executive_summary: str
    overall_assessment: QualitativeJudgment
    sections: list[ConclusionBriefSection] = Field(default_factory=list)
    cross_cutting_insights: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    generated_at: str = ""
