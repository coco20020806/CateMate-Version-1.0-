"""Merge completed clarification answers into RequirementUnderstandingSpec via LLM."""

from __future__ import annotations

from typing import Any

from catemate.ai.client import CateMateAIClient
from catemate.understanding.clarification import SKIPPED_ANSWER, normalize_clarifying_question_ids
from catemate.understanding.generator import _validate_spec
from catemate.understanding.prompt_builder import build_requirement_understanding_messages
from catemate.understanding.readiness import normalize_understanding_readiness
from catemate.understanding.schemas import RequirementUnderstandingSpec, UserAnswer


def build_clarification_answer_payload(spec: RequirementUnderstandingSpec) -> list[dict[str, Any]]:
    """Structure user_answers with matching clarifying question text for the updater prompt."""
    question_by_id = {question.question_id: question for question in spec.clarifying_questions}
    payload: list[dict[str, Any]] = []
    for answer in spec.user_answers:
        question = question_by_id.get(answer.question_id)
        payload.append(
            {
                "question_id": answer.question_id,
                "question": question.question if question else "",
                "answer": answer.answer,
                "skipped": answer.answer == SKIPPED_ANSWER,
                "default_assumption": question.default_assumption if question else "",
                "answered_at": answer.answered_at,
            }
        )
    return payload


def needs_clarification_merge(spec: RequirementUnderstandingSpec) -> bool:
    """Return True when clarification Q&A should be merged into understood fields."""
    return bool(spec.clarifying_questions and spec.user_answers)


def merge_clarification_answers_into_understanding(
    spec: RequirementUnderstandingSpec,
    ai_client: CateMateAIClient,
    *,
    data_module_summaries: list[dict[str, Any]] | None = None,
) -> RequirementUnderstandingSpec:
    """One LLM call to fold all clarification answers into understood / assumptions / summary."""
    if not needs_clarification_merge(spec):
        return spec

    batch_answers = build_clarification_answer_payload(spec)
    messages = build_requirement_understanding_messages(
        request_text=spec.original_request,
        data_module_summaries=data_module_summaries,
        previous_spec=spec.model_dump(mode="json"),
        user_answers=batch_answers,
    )
    payload = ai_client.complete_json(messages)
    updated = _validate_spec(payload, original_request=spec.original_request)
    updated = _preserve_clarification_records(spec, updated)
    updated = normalize_clarifying_question_ids(updated)
    return normalize_understanding_readiness(updated)


def _preserve_clarification_records(
    previous: RequirementUnderstandingSpec,
    updated: RequirementUnderstandingSpec,
) -> RequirementUnderstandingSpec:
    """Keep original_request, user_answers, and stable case_id after LLM merge."""
    merged_answers = _dedupe_user_answers(list(previous.user_answers) + list(updated.user_answers))
    return updated.model_copy(
        update={
            "case_id": updated.case_id or previous.case_id,
            "original_request": previous.original_request,
            "user_answers": merged_answers,
            "clarifying_questions": previous.clarifying_questions or updated.clarifying_questions,
        }
    )


def _dedupe_user_answers(answers: list[UserAnswer]) -> list[UserAnswer]:
    seen: set[tuple[str, str]] = set()
    deduped: list[UserAnswer] = []
    for item in answers:
        key = (item.question_id, item.answer)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
