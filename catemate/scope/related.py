"""if_related: Sub-L3 item relevance filtering via concept pack scoring."""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

from catemate.scope.concept_schemas import RelatedConceptPack

ITEM_NAME_COLUMN = "item_name"
TRANSLATION_COLUMN = "translation"

STRONG_SMART_TERMS = frozenset(
    {
        "smart",
        "wifi",
        "wi-fi",
        "app",
        "bluetooth",
        "智能",
        "无线",
        "蓝牙",
    }
)

SMART_SCORE_PER_HIT = 0.15
SMART_SCORE_CAP = 0.45
STRONG_SMART_BONUS = 0.20
PET_CONTEXT_SCORE = 0.15
BOOST_SCORE = 0.10


def apply_if_related(
    df: pd.DataFrame,
    pack: RelatedConceptPack,
    *,
    min_score: float | None = None,
) -> pd.DataFrame:
    """Filter rows to items matching the related concept pack."""
    if pack is None or df.empty:
        return df.copy()

    if ITEM_NAME_COLUMN not in df.columns:
        return df.copy()

    threshold = pack.min_score if min_score is None else min_score
    working = df.copy()
    working["_search_text"] = _build_search_text(working)

    unique_titles = working.drop_duplicates(subset=[ITEM_NAME_COLUMN], keep="first")
    scores = unique_titles["_search_text"].map(lambda text: _score_text(text, pack))
    matched_terms = unique_titles["_search_text"].map(lambda text: _matched_terms(text, pack))

    title_scores = pd.DataFrame(
        {
            ITEM_NAME_COLUMN: unique_titles[ITEM_NAME_COLUMN].values,
            "related_score": scores.values,
            "related_matched_terms": matched_terms.values,
        }
    )
    title_scores["is_related"] = title_scores["related_score"] >= threshold

    result = working.merge(title_scores, on=ITEM_NAME_COLUMN, how="left")
    result = result[result["is_related"].fillna(False)].drop(columns=["_search_text"])
    return result.reset_index(drop=True)


def _build_search_text(df: pd.DataFrame) -> pd.Series:
    name = df[ITEM_NAME_COLUMN].fillna("").astype(str)
    if TRANSLATION_COLUMN in df.columns:
        translation = df[TRANSLATION_COLUMN].fillna("").astype(str)
        combined = (name + " " + translation).str.strip()
    else:
        combined = name.str.strip()
    return combined.str.lower()


def _compile_patterns(terms: Iterable[str]) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for term in terms:
        cleaned = str(term).strip()
        if not cleaned:
            continue
        if _looks_like_regex(cleaned):
            patterns.append(re.compile(cleaned, re.IGNORECASE))
        else:
            patterns.append(re.compile(re.escape(cleaned), re.IGNORECASE))
    return patterns


def _looks_like_regex(term: str) -> bool:
    regex_markers = ("\\b", "\\s", "(", ")", "[", "]", "|", ".*", ".+")
    return any(marker in term for marker in regex_markers)


def _hit_patterns(text: str, patterns: list[re.Pattern[str]]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if pattern.search(text):
            hits.append(pattern.pattern)
    return hits


def _score_text(text: str, pack: RelatedConceptPack) -> float:
    normalized = text.lower().strip()
    if not normalized:
        return 0.0

    smart_patterns = _compile_patterns(pack.smart_signals)
    pet_patterns = _compile_patterns(pack.pet_context)
    boost_patterns = _compile_patterns(pack.boost_terms)
    exclude_patterns = _compile_patterns(pack.exclude_terms)

    if _hit_patterns(normalized, exclude_patterns):
        return 0.0

    smart_hits = _hit_patterns(normalized, smart_patterns)
    if not smart_hits:
        return 0.0

    pet_hits = _hit_patterns(normalized, pet_patterns)
    if not pet_hits:
        return 0.0

    score = min(len(smart_hits) * SMART_SCORE_PER_HIT, SMART_SCORE_CAP)
    if _has_strong_smart_term(normalized):
        score += STRONG_SMART_BONUS
    score += PET_CONTEXT_SCORE

    boost_hits = _hit_patterns(normalized, boost_patterns)
    if boost_hits:
        score += BOOST_SCORE

    return round(min(score, 1.0), 4)


def _matched_terms(text: str, pack: RelatedConceptPack) -> str:
    normalized = text.lower().strip()
    groups = [
        ("smart", pack.smart_signals),
        ("pet", pack.pet_context),
        ("boost", pack.boost_terms),
        ("exclude", pack.exclude_terms),
    ]
    parts: list[str] = []
    for label, terms in groups:
        hits = _hit_patterns(normalized, _compile_patterns(terms))
        if hits:
            parts.append(f"{label}={','.join(hits[:5])}")
    return "; ".join(parts)


def _has_strong_smart_term(text: str) -> bool:
    lowered = text.lower()
    for term in STRONG_SMART_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", lowered, re.IGNORECASE):
            return True
        if term in lowered:
            return True
    return False
