"""Enrich confirmation template rows from case config analysis plan."""

from __future__ import annotations

from catemate.schemas.category_requirement import CategoryAnalysisCaseConfig, ConfirmationTemplateItem


def enrich_confirmation_templates(config: CategoryAnalysisCaseConfig) -> CategoryAnalysisCaseConfig:
    """Fill confirmation template question/reason from analysis_plan and case fields."""
    if not config.confirmation_templates:
        return config

    analysis_by_block = {row.analysis_block.strip(): row for row in config.analysis_plan if row.analysis_block}
    field_values = {
        "时间范围": config.time_range,
        "交付对象": config.delivery_audience,
        "类目定位": config.target_category_text,
    }

    enriched: list[ConfirmationTemplateItem] = []
    for template in config.confirmation_templates:
        question = template.question.strip()
        reason = template.reason.strip()
        suggested = template.suggested_value.strip()

        plan_row = analysis_by_block.get(template.name.strip())
        if plan_row is None:
            for block, row in analysis_by_block.items():
                if template.name.strip() in block or block in template.name.strip():
                    plan_row = row
                    break

        if plan_row is not None:
            if not question:
                question = plan_row.question.strip()
            if not reason:
                reason = plan_row.note.strip()

        if not suggested:
            suggested = field_values.get(template.name.strip(), "")

        enriched.append(
            template.model_copy(
                update={
                    "question": question,
                    "reason": reason or question,
                    "suggested_value": suggested,
                }
            )
        )

    return config.model_copy(update={"confirmation_templates": enriched})
