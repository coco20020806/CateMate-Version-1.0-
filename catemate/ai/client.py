"""Thin OpenAI-SDK wrapper used by CateMate planning."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from catemate.ai.settings import AISettings


class CateMateAIClient:
    """Minimal chat client with text and JSON helpers."""

    def __init__(self, settings: AISettings):
        self.settings = settings
        self._client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)

    def complete_text(self, messages: list[dict[str, str]]) -> str:
        """Return model text content for a chat completion."""
        kwargs: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
        }
        if self.settings.max_tokens is not None:
            kwargs["max_tokens"] = self.settings.max_tokens

        response = self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("AI response content is empty.")
        return content.strip()

    def complete_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Return a parsed JSON object from a chat completion."""
        kwargs: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
            "response_format": {"type": "json_object"},
        }
        if self.settings.max_tokens is not None:
            kwargs["max_tokens"] = self.settings.max_tokens

        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as first_error:
            # Some OpenAI-compatible servers may not support response_format.
            kwargs.pop("response_format", None)
            try:
                response = self._client.chat.completions.create(**kwargs)
            except Exception as second_error:
                raise RuntimeError(
                    "AI chat completion failed. "
                    f"First error: {first_error}; retry without response_format: {second_error}"
                ) from second_error

        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("AI JSON response content is empty.")

        text = content.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            snippet = text[:500]
            raise ValueError(
                "AI returned content that is not valid JSON. "
                f"Parse error: {exc}. Content snippet: {snippet!r}"
            ) from exc

        if not isinstance(payload, dict):
            snippet = text[:500]
            raise ValueError(
                "AI JSON root must be an object/dict. "
                f"Got type={type(payload).__name__}. Content snippet: {snippet!r}"
            )
        return payload
