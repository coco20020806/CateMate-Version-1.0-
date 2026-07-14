"""Pydantic schemas for human confirmation flow."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from catemate.schemas.enums import ConfirmationStatus


class ConfirmationItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    status: ConfirmationStatus
    suggested_value: str = ""
    reason: str = ""
    source: str = ""
    planning_question_id: str = ""
    # When set, workbook writers may use this for the block column.
    # confirmation gate still keys off status only.
    blocks_ppt_ready: bool | None = None


class GateResult(BaseModel):
    can_generate: bool
    blocking_items: list[ConfirmationItem]
    message: str
