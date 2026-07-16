"""Validate ReportBlueprint sections against module catalog."""

from __future__ import annotations

from typing import Any

from catemate.core.output_policy import (
    is_forbidden_module,
    is_forbidden_presentation,
    section_has_daily_wording,
    validate_output_grain,
)
from catemate.orchestration.schemas import ReportBlueprint

_VALID_GRAINS = {"category", "shop", "item"}


def validate_blueprint_against_catalog(
    blueprint: ReportBlueprint,
    catalog: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    """Return (is_valid, error_messages)."""
    errors: list[str] = []

    if not blueprint.sections:
        errors.append("blueprint must contain at least one section")
        return False, errors

    catalog_by_id = {
        str(entry.get("module_id") or "").strip(): entry
        for entry in catalog
        if str(entry.get("module_id") or "").strip()
    }

    seen_section_ids: set[str] = set()
    for index, section in enumerate(blueprint.sections, start=1):
        prefix = f"sections[{index}] ({section.section_id or 'missing section_id'})"

        section_id = section.section_id.strip()
        if not section_id:
            errors.append(f"{prefix}: section_id is required")
            continue
        if section_id in seen_section_ids:
            errors.append(f"{prefix}: duplicate section_id")
        seen_section_ids.add(section_id)

        if not section.title.strip():
            errors.append(f"{prefix}: title is required")
        if not section.sub_question.strip():
            errors.append(f"{prefix}: sub_question is required")

        module_id = section.module_id.strip()
        metric_id = section.metric_id.strip()
        grain = section.grain.strip()

        if not module_id:
            errors.append(f"{prefix}: module_id is required")
            continue
        if not metric_id:
            errors.append(f"{prefix}: metric_id is required")
            continue
        if not grain:
            errors.append(f"{prefix}: grain is required")
            continue

        if grain not in _VALID_GRAINS:
            errors.append(f"{prefix}: invalid grain {grain!r}")

        module_entry = catalog_by_id.get(module_id)
        if module_entry is None:
            errors.append(f"{prefix}: unknown module_id {module_id!r}")
            continue

        if is_forbidden_module(module_id):
            errors.append(f"{prefix}: module_id {module_id!r} is forbidden by output grain policy")

        presentation = str(section.expected_shape.presentation or "").strip()
        if is_forbidden_presentation(presentation):
            errors.append(
                f"{prefix}: presentation {presentation!r} is forbidden by output grain policy"
            )

        shape_grains = [str(g) for g in section.expected_shape.grain or []]
        grain_violations = validate_output_grain(shape_grains)
        if grain_violations:
            errors.append(
                f"{prefix}: expected_shape.grain contains forbidden values {grain_violations}"
            )

        if section_has_daily_wording(section.title, section.sub_question):
            errors.append(f"{prefix}: section wording implies daily output, which is forbidden")

        allowed_grains = [str(g) for g in module_entry.get("allowed_grains") or []]
        if allowed_grains and grain not in allowed_grains:
            errors.append(
                f"{prefix}: grain {grain!r} not in allowed_grains {allowed_grains}"
            )

        allowed_metrics = [str(m) for m in module_entry.get("allowed_metrics") or []]
        if allowed_metrics and metric_id not in allowed_metrics:
            errors.append(
                f"{prefix}: metric_id {metric_id!r} not in allowed_metrics {allowed_metrics}"
            )

        shape_metrics = [str(m) for m in section.expected_shape.metrics or []]
        if shape_metrics and metric_id not in shape_metrics:
            errors.append(
                f"{prefix}: expected_shape.metrics {shape_metrics} must include metric_id {metric_id!r}"
            )

    return len(errors) == 0, errors
