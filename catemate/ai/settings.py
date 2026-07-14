"""AI provider settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


PROVIDER_DEEPSEEK = "deepseek"
PROVIDER_OPENAI_COMPATIBLE = "openai_compatible"
DEFAULT_PROVIDER = PROVIDER_OPENAI_COMPATIBLE

DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-pro"
OPENAI_COMPATIBLE_DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1"
OPENAI_COMPATIBLE_DEFAULT_API_KEY = "pwd"
OPENAI_COMPATIBLE_DEFAULT_MODEL = "gpt-5.5"


@dataclass(frozen=True)
class AISettings:
    provider: str
    model: str
    base_url: str
    api_key: str
    temperature: float = 0.2
    max_tokens: int | None = None

    @classmethod
    def from_env(cls) -> "AISettings":
        """Build settings from environment variables."""
        provider = (os.getenv("CATEMATE_AI_PROVIDER") or DEFAULT_PROVIDER).strip().lower()

        if provider == PROVIDER_DEEPSEEK:
            api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
            if not api_key:
                raise ValueError("Missing DEEPSEEK_API_KEY for provider=deepseek")
            model = (os.getenv("DEEPSEEK_MODEL") or DEEPSEEK_DEFAULT_MODEL).strip()
            base_url = (os.getenv("DEEPSEEK_BASE_URL") or DEEPSEEK_DEFAULT_BASE_URL).strip()
            return cls(
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
                temperature=_read_float("CATEMATE_AI_TEMPERATURE", 0.2),
                max_tokens=_read_optional_int("CATEMATE_AI_MAX_TOKENS"),
            )

        if provider == PROVIDER_OPENAI_COMPATIBLE:
            api_key = (
                os.getenv("CATEMATE_OPENAI_API_KEY") or OPENAI_COMPATIBLE_DEFAULT_API_KEY
            ).strip()
            base_url = (
                os.getenv("CATEMATE_OPENAI_BASE_URL") or OPENAI_COMPATIBLE_DEFAULT_BASE_URL
            ).strip()
            model = (
                os.getenv("CATEMATE_OPENAI_MODEL") or OPENAI_COMPATIBLE_DEFAULT_MODEL
            ).strip()
            return cls(
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
                temperature=_read_float("CATEMATE_AI_TEMPERATURE", 0.2),
                max_tokens=_read_optional_int("CATEMATE_AI_MAX_TOKENS"),
            )

        raise ValueError(
            f"Unsupported CATEMATE_AI_PROVIDER={provider!r}. "
            f"Supported values: {PROVIDER_DEEPSEEK}, {PROVIDER_OPENAI_COMPATIBLE}."
        )


def _read_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid float for {name}: {raw!r}") from exc


def _read_optional_int(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {raw!r}") from exc
