"""Global output time-grain policy for solve-loop orchestration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from catemate.core.paths import CONFIG_DIR

POLICY_PATH = CONFIG_DIR / "output_grain_policy.yaml"

_DAILY_TIME_RANGE_MARKERS = (
    "近30天",
    "近 30 天",
    "30天",
    "按天",
    "日度",
    "daily",
    "day-by-day",
    "per day",
)

_DAILY_SECTION_MARKERS = (
    "日度",
    "近30天",
    "近 30 天",
    "按天",
    "daily",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyYAML is required to read output_grain_policy.yaml") from exc
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return dict(payload) if isinstance(payload, dict) else {}


@lru_cache(maxsize=1)
def load_output_grain_policy(path: Path | None = None) -> dict[str, Any]:
    """Load output grain policy from config/output_grain_policy.yaml."""
    return _load_yaml(path or POLICY_PATH)


def clear_output_grain_policy_cache() -> None:
    """Clear cached policy (for tests)."""
    load_output_grain_policy.cache_clear()


def enabled_module_ids() -> tuple[str, ...]:
    policy = load_output_grain_policy()
    modules = policy.get("enabled_v2_modules") or []
    return tuple(str(item).strip() for item in modules if str(item).strip())


def forbidden_module_ids() -> frozenset[str]:
    policy = load_output_grain_policy()
    items = policy.get("forbidden_module_ids") or []
    return frozenset(str(item).strip() for item in items if str(item).strip())


def forbidden_presentations() -> frozenset[str]:
    policy = load_output_grain_policy()
    items = policy.get("forbidden_presentations") or []
    return frozenset(str(item).strip() for item in items if str(item).strip())


def forbidden_output_grains() -> frozenset[str]:
    policy = load_output_grain_policy()
    items = policy.get("forbidden_output_grains") or []
    return frozenset(str(item).strip() for item in items if str(item).strip())


def allowed_output_grains() -> frozenset[str]:
    policy = load_output_grain_policy()
    items = policy.get("allowed_output_grains") or []
    return frozenset(str(item).strip() for item in items if str(item).strip())


def is_forbidden_module(module_id: str) -> bool:
    module_id = str(module_id or "").strip()
    if not module_id:
        return False
    if module_id in forbidden_module_ids():
        return True
    enabled = set(enabled_module_ids())
    return bool(enabled) and module_id not in enabled


def is_forbidden_presentation(presentation: str) -> bool:
    presentation = str(presentation or "").strip()
    return bool(presentation) and presentation in forbidden_presentations()


def validate_output_grain(grain_list: list[str] | None) -> list[str]:
    """Return forbidden grain values found in grain_list."""
    forbidden = forbidden_output_grains()
    if not forbidden:
        return []
    violations: list[str] = []
    for grain in grain_list or []:
        grain_text = str(grain).strip()
        if grain_text in forbidden and grain_text not in violations:
            violations.append(grain_text)
    return violations


def sanitize_output_grains(grain_list: list[str] | None) -> list[str]:
    """Replace forbidden output grains with grass_month."""
    forbidden = forbidden_output_grains()
    if not grain_list:
        return []
    sanitized: list[str] = []
    for grain in grain_list:
        grain_text = str(grain).strip()
        if not grain_text:
            continue
        if grain_text in forbidden:
            replacement = "grass_month"
            if replacement not in sanitized:
                sanitized.append(replacement)
            continue
        if grain_text not in sanitized:
            sanitized.append(grain_text)
    return sanitized


def sanitize_presentation(presentation: str) -> str:
    presentation = str(presentation or "").strip() or "table"
    if is_forbidden_presentation(presentation):
        return "trend_table"
    return presentation


def default_time_range_text() -> str:
    policy = load_output_grain_policy()
    text = str(policy.get("default_time_range") or "").strip()
    if text:
        return text
    return "按源数据最新可用完整月份及此前若干月聚合；禁止日度窗口。"


def time_range_guidance_text() -> str:
    policy = load_output_grain_policy()
    text = str(policy.get("time_range_interpretation") or "").strip()
    if text:
        return text
    return default_time_range_text()


def normalize_time_range_text(time_range: str) -> str:
    """Rewrite daily-oriented time_range wording to monthly policy text."""
    text = str(time_range or "").strip()
    if not text:
        return default_time_range_text()
    lowered = text.lower()
    if any(marker in text or marker in lowered for marker in _DAILY_TIME_RANGE_MARKERS):
        return default_time_range_text()
    return text


def section_has_daily_wording(*texts: str) -> bool:
    combined = " ".join(str(text or "") for text in texts)
    lowered = combined.lower()
    return any(marker in combined or marker in lowered for marker in _DAILY_SECTION_MARKERS)


def map_daily_performance_intent(intents: list[str], *, original_request: str = "") -> list[str]:
    """Map daily_performance to market_trend unless user explicitly asked for daily."""
    if "daily_performance" not in intents:
        return intents
    request = str(original_request or "")
    request_lower = request.lower()
    explicit_daily = any(
        marker in request or marker in request_lower for marker in _DAILY_TIME_RANGE_MARKERS
    )
    if explicit_daily:
        return intents
    mapped = ["market_trend" if item == "daily_performance" else item for item in intents]
    deduped: list[str] = []
    for item in mapped:
        if item not in deduped:
            deduped.append(item)
    return deduped
