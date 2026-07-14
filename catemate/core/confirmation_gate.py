"""Confirmation gate before generating PPT-ready workbooks."""

from __future__ import annotations

from catemate.schemas.confirmation import ConfirmationItem, GateResult
from catemate.schemas.enums import ConfirmationStatus


STATUS_CONFIRMED = ConfirmationStatus.CONFIRMED.value
STATUS_NOT_NEEDED = ConfirmationStatus.NOT_NEEDED.value
STATUS_PENDING_CONFIRMATION = ConfirmationStatus.PENDING_CONFIRMATION.value
STATUS_PENDING_SUPPLEMENT = ConfirmationStatus.PENDING_SUPPLEMENT.value
STATUS_SUPPLEMENTED = ConfirmationStatus.SUPPLEMENTED.value
STATUS_BLOCKED = ConfirmationStatus.BLOCKED.value

ALLOWED_FINAL_STATUSES = {ConfirmationStatus.CONFIRMED, ConfirmationStatus.NOT_NEEDED}
BLOCKING_STATUSES = {
    ConfirmationStatus.PENDING_CONFIRMATION,
    ConfirmationStatus.PENDING_SUPPLEMENT,
    ConfirmationStatus.SUPPLEMENTED,
    ConfirmationStatus.BLOCKED,
}


def evaluate_confirmation_gate(items: list[ConfirmationItem]) -> GateResult:
    """Return whether PPT-ready workbook generation is allowed."""
    blocking_items = [
        item
        for item in items
        if item.blocks_ppt_ready is not False and item.status not in ALLOWED_FINAL_STATUSES
    ]
    if blocking_items:
        return GateResult(
            can_generate=False,
            blocking_items=blocking_items,
            message="\u4ecd\u6709\u786e\u8ba4\u9879\u672a\u5b8c\u6210\uff0c\u4e0d\u80fd\u751f\u6210 PPT-ready workbook\u3002",
        )
    return GateResult(
        can_generate=True,
        blocking_items=[],
        message="\u6240\u6709\u786e\u8ba4\u9879\u5747\u5df2\u901a\u8fc7\uff0c\u53ef\u4ee5\u751f\u6210 PPT-ready workbook\u3002",
    )


def next_status_after_user_supplement() -> str:
    """User-provided data must be rechecked before becoming confirmed."""
    return ConfirmationStatus.SUPPLEMENTED.value


def status_after_agent_recheck(is_valid: bool, is_required: bool = True) -> str:
    """Convert an Agent data recheck result into the next confirmation status."""
    if is_valid:
        return ConfirmationStatus.CONFIRMED.value
    return ConfirmationStatus.PENDING_SUPPLEMENT.value if is_required else ConfirmationStatus.NOT_NEEDED.value
