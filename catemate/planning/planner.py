"""Requirement planner that turns planning context into a validated spec."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from catemate.ai.client import CateMateAIClient
from catemate.planning.prompt_builder import build_planning_messages
from catemate.planning.schemas import RequirementPlanningSpec


class RequirementPlanner:
    """Call AI and validate the returned planning JSON."""

    def __init__(self, ai_client: CateMateAIClient):
        self.ai_client = ai_client

    def plan(self, context: dict[str, Any]) -> RequirementPlanningSpec:
        messages = build_planning_messages(context)
        payload = self.ai_client.complete_json(messages)
        try:
            return RequirementPlanningSpec.model_validate(payload)
        except ValidationError as exc:
            snippet = str(payload)[:500]
            raise ValueError(
                "AI returned JSON that failed RequirementPlanningSpec validation. "
                f"Validation error: {exc}. Payload snippet: {snippet!r}"
            ) from exc
