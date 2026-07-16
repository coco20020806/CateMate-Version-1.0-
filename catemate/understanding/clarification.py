"""Clarification gate helpers for RequirementUnderstandingSpec."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from catemate.understanding.schemas import (
    ClarifyingQuestion,
    ConfidenceLevel,
    QuestionCategory,
    RequirementAssumption,
    RequirementUnderstandingSpec,
    UserAnswer,
)

SKIPPED_ANSWER = "[skipped]"


def normalize_clarifying_question_ids(spec: RequirementUnderstandingSpec) -> RequirementUnderstandingSpec:
    """Assign stable unique question_id values when duplicates or placeholders exist."""
    seen: set[str] = set()
    updated_questions: list[ClarifyingQuestion] = []

    for index, question in enumerate(spec.clarifying_questions, start=1):
        question_id = question.question_id.strip()
        if not question_id or question_id == "question" or question_id in seen:
            question_id = f"clarify_{index}"
        while question_id in seen:
            question_id = f"clarify_{index}_{len(seen)}"
        seen.add(question_id)
        updated_questions.append(question.model_copy(update={"question_id": question_id}))

    return spec.model_copy(update={"clarifying_questions": updated_questions})


def answered_question_ids(spec: RequirementUnderstandingSpec) -> set[str]:
    return {answer.question_id for answer in spec.user_answers if answer.question_id.strip()}


def unanswered_clarifying_questions(spec: RequirementUnderstandingSpec) -> list[ClarifyingQuestion]:
    if not spec.clarifying_questions:
        return []
    answered = answered_question_ids(spec)
    return [question for question in spec.clarifying_questions if question.question_id not in answered]


def is_clarification_complete(spec: RequirementUnderstandingSpec) -> bool:
    return len(unanswered_clarifying_questions(spec)) == 0


def rawdata_clarifying_questions(spec: RequirementUnderstandingSpec) -> list[ClarifyingQuestion]:
    return [
        question
        for question in spec.clarifying_questions
        if question.question_category == QuestionCategory.RAWDATA
    ]


def answer_for_question(spec: RequirementUnderstandingSpec, question_id: str) -> str | None:
    for answer in spec.user_answers:
        if answer.question_id == question_id:
            return answer.answer
    return None


def user_declined_rawdata(spec: RequirementUnderstandingSpec) -> bool:
    """True when user skipped at least one rawdata_* clarification (partial data path)."""
    for question in rawdata_clarifying_questions(spec):
        if answer_for_question(spec, question.question_id) == SKIPPED_ANSWER:
            return True
    return False


def all_rawdata_questions_resolved(spec: RequirementUnderstandingSpec) -> bool:
    """All rawdata questions answered or skipped."""
    rawdata = rawdata_clarifying_questions(spec)
    if not rawdata:
        return True
    answered = answered_question_ids(spec)
    return all(question.question_id in answered for question in rawdata)


def requires_clarification_gate(spec: RequirementUnderstandingSpec) -> bool:
    return bool(spec.clarifying_questions)


def apply_clarification_answer(
    spec: RequirementUnderstandingSpec,
    question_id: str,
    *,
    answer_text: str | None = None,
    skipped: bool = False,
) -> RequirementUnderstandingSpec:
    """Record a user answer or skip for one clarifying question."""
    question_id = question_id.strip()
    if not question_id:
        raise ValueError("question_id is empty.")

    question = next((item for item in spec.clarifying_questions if item.question_id == question_id), None)
    if question is None:
        raise ValueError(f"Unknown clarifying question_id: {question_id}")

    if question_id in answered_question_ids(spec):
        raise ValueError(f"Question already answered or skipped: {question_id}")

    if skipped:
        answer_value = SKIPPED_ANSWER
    else:
        answer_value = (answer_text or "").strip()
        if not answer_value:
            raise ValueError("answer_text is empty; use skipped=True to skip.")

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    new_answer = UserAnswer(question_id=question_id, answer=answer_value, answered_at=timestamp)
    updated_answers = list(spec.user_answers) + [new_answer]

    updated_assumptions = list(spec.assumptions)
    if skipped and question.default_assumption.strip():
        assumption_id = f"assumption_from_{question_id}"
        updated_assumptions.append(
            RequirementAssumption(
                assumption_id=assumption_id,
                content=question.default_assumption.strip(),
                confidence=ConfidenceLevel.MEDIUM,
                needs_user_confirmation=False,
            )
        )

    return spec.model_copy(update={"user_answers": updated_answers, "assumptions": updated_assumptions})


def save_understanding_spec(spec: RequirementUnderstandingSpec, path: Path) -> Path:
    """Persist understanding spec JSON to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(spec.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
