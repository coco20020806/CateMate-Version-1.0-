"""Update RequirementUnderstandingSpec with user answers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from catemate.ai.client import CateMateAIClient
from catemate.understanding.generator import _validate_spec
from catemate.understanding.prompt_builder import build_requirement_understanding_messages
from catemate.understanding.readiness import normalize_understanding_readiness
from catemate.understanding.site_normalizer import normalize_target_sites
from catemate.understanding.schemas import RequirementUnderstandingSpec, UserAnswer


class RequirementUnderstandingUpdater:
    """Merge user supplemental answers into an existing understanding spec."""

    def __init__(self, ai_client: CateMateAIClient):
        self.ai_client = ai_client

    def update(
        self,
        existing_spec: RequirementUnderstandingSpec,
        user_answer_text: str,
        *,
        data_module_summaries: list[dict[str, Any]] | None = None,
    ) -> RequirementUnderstandingSpec:
        user_answer_text = user_answer_text.strip()
        if not user_answer_text:
            raise ValueError("user_answer_text is empty.")

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        pending_answer = {
            "question_id": f"free_text_{timestamp.replace(':', '')}",
            "answer": user_answer_text,
            "answered_at": timestamp,
        }

        messages = build_requirement_understanding_messages(
            request_text=existing_spec.original_request,
            data_module_summaries=data_module_summaries,
            previous_spec=existing_spec.model_dump(mode="json"),
            user_answers=[pending_answer],
        )
        payload = self.ai_client.complete_json(messages)
        spec = _validate_spec(payload, original_request=existing_spec.original_request)
        spec = _merge_user_answers(existing_spec, spec, pending_answer)
        spec = normalize_target_sites(spec)
        return normalize_understanding_readiness(spec)


def _merge_user_answers(
    previous: RequirementUnderstandingSpec,
    updated: RequirementUnderstandingSpec,
    new_answer: dict[str, str],
) -> RequirementUnderstandingSpec:
    merged_answers: list[UserAnswer] = list(previous.user_answers)
    merged_answers.append(
        UserAnswer(
            question_id=new_answer["question_id"],
            answer=new_answer["answer"],
            answered_at=new_answer["answered_at"],
        )
    )

    seen: set[tuple[str, str]] = set()
    deduped: list[UserAnswer] = []
    for item in list(updated.user_answers) + merged_answers:
        key = (item.question_id, item.answer)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return updated.model_copy(
        update={
            "case_id": updated.case_id or previous.case_id,
            "original_request": previous.original_request,
            "user_answers": deduped,
        }
    )
