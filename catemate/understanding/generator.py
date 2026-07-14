"""Generate RequirementUnderstandingSpec from natural-language requests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ValidationError

from catemate.ai.client import CateMateAIClient
from catemate.case_generation.context_loader import fallback_case_id, slug_or_empty
from catemate.understanding.prompt_builder import build_requirement_understanding_messages
from catemate.understanding.clarification import normalize_clarifying_question_ids
from catemate.understanding.readiness import normalize_understanding_readiness
from catemate.understanding.schemas import (
    AnalysisIntent,
    ClarifyingQuestion,
    ConfidenceLevel,
    InferredCategoryCandidate,
    QuestionType,
    RequirementAssumption,
    RequirementUnderstandingSpec,
    RequirementUncertainty,
    UnderstandingStatus,
    UnderstoodRequirement,
)


class RequirementUnderstandingGenerator:
    """AI-based generator for RequirementUnderstandingSpec."""

    def __init__(self, ai_client: CateMateAIClient):
        self.ai_client = ai_client

    def generate(
        self,
        request_text: str,
        *,
        data_module_summaries: list[dict[str, Any]] | None = None,
        category_tree_candidates: list[dict[str, str]] | None = None,
    ) -> RequirementUnderstandingSpec:
        messages = build_requirement_understanding_messages(
            request_text=request_text,
            data_module_summaries=data_module_summaries,
            category_tree_candidates=category_tree_candidates,
        )
        payload = self.ai_client.complete_json(messages)
        spec = _validate_spec(payload, original_request=request_text)
        spec = _ensure_case_id(spec)
        spec = normalize_clarifying_question_ids(spec)
        return normalize_understanding_readiness(spec)


def _validate_spec(payload: dict[str, Any], *, original_request: str) -> RequirementUnderstandingSpec:
    normalized = _normalize_understanding_payload(payload, original_request=original_request)
    try:
        return RequirementUnderstandingSpec.model_validate(normalized)
    except ValidationError as exc:
        snippet = str(normalized)[:800]
        raise ValueError(
            "AI returned JSON that failed RequirementUnderstandingSpec validation. "
            f"Validation error: {exc}. Payload snippet: {snippet!r}"
        ) from exc


def _ensure_case_id(spec: RequirementUnderstandingSpec) -> RequirementUnderstandingSpec:
    if spec.case_id.strip():
        return spec
    seed = spec.understood.inferred_category or spec.understood.target_category_text or "case"
    generated = fallback_case_id(seed)
    if slug_or_empty(generated):
        return spec.model_copy(update={"case_id": generated})
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return spec.model_copy(update={"case_id": fallback_case_id("understanding", timestamp=timestamp)})


def _normalize_understanding_payload(
    payload: dict[str, Any],
    *,
    original_request: str,
) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("spec_version", "requirement_understanding_v1")
    normalized["original_request"] = str(normalized.get("original_request") or original_request)

    understood_raw = normalized.get("understood") or {}
    if not isinstance(understood_raw, dict):
        understood_raw = {}
    normalized["understood"] = _normalize_understood(understood_raw)

    normalized["assumptions"] = [
        _normalize_assumption(item)
        for item in _as_list(normalized.get("assumptions"))
        if isinstance(item, dict)
    ]
    normalized["uncertainties"] = [
        _normalize_uncertainty(item)
        for item in _as_list(normalized.get("uncertainties"))
        if isinstance(item, dict)
    ]
    normalized["clarifying_questions"] = [
        _normalize_question(item, index=index)
        for index, item in enumerate(_as_list(normalized.get("clarifying_questions")), start=1)
        if isinstance(item, dict)
    ]
    normalized["user_answers"] = [
        _normalize_user_answer(item)
        for item in _as_list(normalized.get("user_answers"))
        if isinstance(item, dict)
    ]

    status = str(normalized.get("status") or UnderstandingStatus.READY_FOR_MODULE_SELECTION.value)
    if status not in {s.value for s in UnderstandingStatus}:
        status = UnderstandingStatus.READY_FOR_MODULE_SELECTION.value
    normalized["status"] = status

    readiness = normalized.get("readiness") or {}
    if not isinstance(readiness, dict):
        readiness = {}
    normalized["readiness"] = {
        "can_select_modules": bool(readiness.get("can_select_modules", True)),
        "blocking_reasons": _as_str_list(readiness.get("blocking_reasons")),
        "non_blocking_notes": _as_str_list(readiness.get("non_blocking_notes")),
    }
    return normalized


def _normalize_understood(raw: dict[str, Any]) -> dict[str, Any]:
    intents: list[str] = []
    for item in _as_list(raw.get("analysis_intents")):
        value = str(item).strip().lower()
        if value in {intent.value for intent in AnalysisIntent}:
            intents.append(value)
        elif value:
            intents.append(AnalysisIntent.UNKNOWN.value)
    if not intents:
        intents = [AnalysisIntent.UNKNOWN.value]

    metric_definitions = raw.get("metric_definitions") or {}
    if not isinstance(metric_definitions, dict):
        metric_definitions = {}

    candidate_rows = [
        _normalize_inferred_category_candidate(item)
        for item in _as_list(raw.get("inferred_category_candidates"))
        if isinstance(item, dict)
    ]

    return {
        "business_background": str(raw.get("business_background") or ""),
        "delivery_audience": str(raw.get("delivery_audience") or "待确认"),
        "delivery_format": str(raw.get("delivery_format") or "Excel"),
        "target_sites": _as_str_list(raw.get("target_sites")),
        "target_category_text": str(raw.get("target_category_text") or ""),
        "inferred_category": str(raw.get("inferred_category") or ""),
        "inferred_category_candidates": candidate_rows,
        "category_level_hint": str(raw.get("category_level_hint") or "unknown"),
        "analysis_intents": intents,
        "time_range": str(raw.get("time_range") or "使用源数据可覆盖范围，待确认"),
        "output_expectation": str(
            raw.get("output_expectation") or "数据需求 workbook / PPT-ready workbook"
        ),
        "metric_definitions": {str(k): str(v) for k, v in metric_definitions.items()},
    }


def _normalize_assumption(item: dict[str, Any]) -> dict[str, Any]:
    confidence = str(item.get("confidence") or ConfidenceLevel.MEDIUM.value).lower()
    if confidence not in {c.value for c in ConfidenceLevel}:
        confidence = ConfidenceLevel.MEDIUM.value
    return {
        "assumption_id": str(item.get("assumption_id") or item.get("id") or "assumption"),
        "content": str(item.get("content") or item.get("assumption") or ""),
        "confidence": confidence,
        "needs_user_confirmation": bool(item.get("needs_user_confirmation", True)),
    }


def _normalize_inferred_category_candidate(item: dict[str, Any]) -> dict[str, Any]:
    confidence = str(item.get("confidence") or ConfidenceLevel.MEDIUM.value).lower()
    if confidence not in {c.value for c in ConfidenceLevel}:
        confidence = ConfidenceLevel.MEDIUM.value
    l1 = str(item.get("l1") or "").strip()
    l2 = str(item.get("l2") or "").strip()
    l3 = str(item.get("l3") or "").strip()
    category_path = str(item.get("category_path") or "").strip()
    if not category_path:
        category_path = " > ".join(part for part in [l1, l2, l3] if part)
    return {
        "l1": l1,
        "l2": l2,
        "l3": l3,
        "category_path": category_path,
        "reason": str(item.get("reason") or ""),
        "confidence": confidence,
    }


def _normalize_uncertainty(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "uncertainty_id": str(item.get("uncertainty_id") or item.get("id") or "uncertainty"),
        "topic": str(item.get("topic") or ""),
        "description": str(item.get("description") or ""),
        "blocks_module_selection": bool(item.get("blocks_module_selection", False)),
    }


def _normalize_question(item: dict[str, Any], *, index: int = 1) -> dict[str, Any]:
    answer_type = str(item.get("expected_answer_type") or QuestionType.FREE_TEXT.value).lower()
    if answer_type not in {q.value for q in QuestionType}:
        answer_type = QuestionType.FREE_TEXT.value
    raw_id = str(item.get("question_id") or item.get("id") or "").strip()
    question_id = raw_id if raw_id and raw_id != "question" else f"clarify_{index}"
    return {
        "question_id": question_id,
        "question": str(item.get("question") or ""),
        "reason": str(item.get("reason") or ""),
        "expected_answer_type": answer_type,
        "options": _as_str_list(item.get("options")),
        "blocks_module_selection": bool(item.get("blocks_module_selection", False)),
        "default_assumption": str(item.get("default_assumption") or ""),
    }


def _normalize_user_answer(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": str(item.get("question_id") or ""),
        "answer": str(item.get("answer") or ""),
        "answered_at": str(item.get("answered_at") or ""),
    }


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value is None or value == "":
        return []
    return [str(value)]
