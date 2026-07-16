"""Generate RelatedConceptPack from user request via LLM."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from catemate.ai.client import CateMateAIClient
from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.understanding.schemas import RequirementUnderstandingSpec
from catemate.understanding.sub_l3_detector import infer_sub_l3_concept

SYSTEM_PROMPT = """你是 CateMate 的 Sub-L3 概念包生成器。

任务：根据用户需求、已映射的 L3 类目和目标站点，生成 RelatedConceptPack JSON，用于 item_name 相关性过滤。

硬性规则：
1. 只输出合法 JSON 对象，不要 Markdown 或解释。
2. concept_id 使用 snake_case 英文。
3. 采用宽定义：智能宠物碗类需求应包含 fountain、dispenser、feeder 等智能喂养设备。
4. 必须提供多语言 smart_signals（英文 + 中文 + 目标站点常用语言）。
5. exclude_terms 必须覆盖常见误报：家禽(chicken/poultry)、慢食碗(slow feed/maze)、配件(replacement/filter only)。
6. pet_context 覆盖 cat/dog/pet 及常见当地语言写法。
7. min_score 默认 0.55。
"""


class ConceptPackGenerator:
    """LLM-backed generator for RelatedConceptPack."""

    def __init__(self, ai_client: CateMateAIClient):
        self.ai_client = ai_client

    def generate(self, spec: RequirementUnderstandingSpec) -> RelatedConceptPack:
        sub_l3 = infer_sub_l3_concept(spec)
        understood = spec.understood
        category_path = understood.inferred_category or understood.target_category_text
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "original_request": spec.original_request,
                        "display_name": sub_l3.display_name,
                        "concept_id": sub_l3.concept_id,
                        "parent_l3": sub_l3.parent_l3,
                        "category_path": category_path,
                        "target_sites": understood.target_sites,
                        "scope_definition": (
                            "宽定义：包含智能饮水器、自动喂食器、喷泉等电动/联网喂养设备；"
                            "排除普通慢食碗、家禽饮水器、配件滤芯。"
                        ),
                        "required_json_shape": {
                            "concept_id": "snake_case",
                            "display_name": "中文或用户用语",
                            "parent_l3": "Bowls & Feeders",
                            "scope_note": "范围说明",
                            "smart_signals": ["smart", "automatic", "fountain", "智能", "..."],
                            "pet_context": ["pet", "cat", "dog", "猫", "狗", "..."],
                            "boost_terms": ["fountain", "dispenser", "feeder", "..."],
                            "exclude_terms": ["chicken", "poultry", "slow feed", "..."],
                            "min_score": 0.55,
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        ]
        try:
            payload = self.ai_client.complete_json(messages)
            return _validate_pack(payload, fallback=sub_l3)
        except (RuntimeError, ValueError, ValidationError):
            return build_fallback_concept_pack(spec, sub_l3=sub_l3)


def build_fallback_concept_pack(
    spec: RequirementUnderstandingSpec,
    *,
    sub_l3=None,
) -> RelatedConceptPack:
    """Deterministic fallback when LLM generation fails."""
    if sub_l3 is None:
        sub_l3 = infer_sub_l3_concept(spec)
    understood = spec.understood
    text = f"{spec.original_request} {understood.target_category_text}".lower()

    smart_signals = ["smart", "automatic", "auto", "electric", "wireless", "fountain", "dispenser", "feeder", "智能", "自动"]
    pet_context = ["pet", "cat", "dog", "猫", "狗"]
    boost_terms = ["fountain", "dispenser", "feeder", "sensor", "filter"]
    exclude_terms = ["chicken", "poultry", "bird", "slow feed", "maze", "replacement"]

    if understood.target_sites:
        for site in understood.target_sites:
            site = site.upper()
            if site in {"ID", "MY"}:
                smart_signals.extend(["pintar", "otomatis"])
            if site == "VN":
                smart_signals.extend(["tự động", "điện"])
            if site == "TH":
                smart_signals.extend(["อัตโนมัติ"])

    tokens = [token for token in re.split(r"[\s/>,&]+", text) if len(token) >= 2]
    smart_signals.extend(token for token in tokens[:6] if token not in smart_signals)

    return RelatedConceptPack(
        concept_id=sub_l3.concept_id or "sub_l3_concept",
        display_name=sub_l3.display_name or understood.target_category_text or "精准子集",
        parent_l3=sub_l3.parent_l3,
        scope_note="LLM fallback：宽定义智能喂养设备",
        smart_signals=_dedupe(smart_signals),
        pet_context=_dedupe(pet_context),
        boost_terms=_dedupe(boost_terms),
        exclude_terms=_dedupe(exclude_terms),
        min_score=0.55,
    )


def enrich_understanding_with_related_concept(
    spec: RequirementUnderstandingSpec,
    ai_client: CateMateAIClient | None = None,
) -> RequirementUnderstandingSpec:
    """Attach sub-L3 metadata and concept pack when the request is narrower than L3."""
    from catemate.understanding.sub_l3_detector import should_generate_concept_pack

    if not should_generate_concept_pack(spec):
        return spec

    sub_l3 = infer_sub_l3_concept(spec)
    understood = spec.understood.model_copy(update={"sub_l3_concept": sub_l3})

    if ai_client is not None:
        pack = ConceptPackGenerator(ai_client).generate(spec.model_copy(update={"understood": understood}))
    else:
        pack = build_fallback_concept_pack(spec.model_copy(update={"understood": understood}), sub_l3=sub_l3)

    intents = list(understood.analysis_intents)
    from catemate.understanding.schemas import AnalysisIntent

    if AnalysisIntent.TOP_LISTING not in intents:
        intents.append(AnalysisIntent.TOP_LISTING)

    understood = understood.model_copy(
        update={
            "related_concept_pack": pack,
            "analysis_intents": intents,
        }
    )
    return spec.model_copy(update={"understood": understood})


def _validate_pack(payload: dict[str, Any], *, fallback) -> RelatedConceptPack:
    normalized = dict(payload)
    normalized.setdefault("concept_id", fallback.concept_id)
    normalized.setdefault("display_name", fallback.display_name)
    normalized.setdefault("parent_l3", fallback.parent_l3)
    for field in ("smart_signals", "pet_context", "boost_terms", "exclude_terms"):
        value = normalized.get(field) or []
        if not isinstance(value, list):
            value = [str(value)]
        normalized[field] = [str(item).strip() for item in value if str(item).strip()]
    return RelatedConceptPack.model_validate(normalized)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
