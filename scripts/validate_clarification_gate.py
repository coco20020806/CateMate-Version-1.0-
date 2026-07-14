"""Validate clarification gate helpers and pipeline resume preconditions."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.understanding.clarification import (
    apply_clarification_answer,
    is_clarification_complete,
    normalize_clarifying_question_ids,
    unanswered_clarifying_questions,
)
from catemate.understanding.clarification_merge import (
    build_clarification_answer_payload,
    needs_clarification_merge,
)
from catemate.understanding.schemas import (
    ClarifyingQuestion,
    RequirementReadiness,
    RequirementUnderstandingSpec,
    UnderstandingStatus,
    UnderstoodRequirement,
)


def _sample_spec() -> RequirementUnderstandingSpec:
    spec = RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="测试需求",
        understood=UnderstoodRequirement(target_sites=["SG"]),
        clarifying_questions=[
            ClarifyingQuestion(question_id="clarify_1", question="问题一？"),
            ClarifyingQuestion(
                question_id="clarify_2",
                question="问题二？",
                default_assumption="按默认假设处理",
            ),
        ],
        readiness=RequirementReadiness(can_select_modules=True),
    )
    return normalize_clarifying_question_ids(spec)


def main() -> int:
    spec = _sample_spec()
    assert not is_clarification_complete(spec)
    assert len(unanswered_clarifying_questions(spec)) == 2

    spec = apply_clarification_answer(spec, "clarify_1", answer_text="回答一")
    assert not is_clarification_complete(spec)
    assert len(unanswered_clarifying_questions(spec)) == 1

    spec = apply_clarification_answer(spec, "clarify_2", skipped=True)
    assert is_clarification_complete(spec)
    assert len(unanswered_clarifying_questions(spec)) == 0
    assert any(item.assumption_id == "assumption_from_clarify_2" for item in spec.assumptions)

    assert needs_clarification_merge(spec)
    payload = build_clarification_answer_payload(spec)
    assert len(payload) == 2
    assert payload[0]["question_id"] == "clarify_1"
    assert payload[1]["skipped"] is True

    empty = _sample_spec().model_copy(update={"user_answers": []})
    assert not needs_clarification_merge(empty)

    print("validate_clarification_gate: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
