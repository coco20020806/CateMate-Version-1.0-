"""Validate category confirmation gate helpers."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.understanding.category_confirmation import (
    can_confirm_selection,
    confirm_categories,
    initialize_category_positioning,
    is_category_confirmation_complete,
)
from catemate.understanding.schemas import (
    RequirementReadiness,
    RequirementUnderstandingSpec,
    UnderstandingStatus,
    UnderstoodRequirement,
)


def main() -> None:
    spec = RequirementUnderstandingSpec(
        status=UnderstandingStatus.READY_FOR_MODULE_SELECTION,
        original_request="新加坡和越南市场的智能宠物碗的类目趋势与产品概括",
        understood=UnderstoodRequirement(target_category_text="智能宠物碗"),
        readiness=RequirementReadiness(can_select_modules=True),
    )
    assert not is_category_confirmation_complete(spec)

    spec = initialize_category_positioning(spec)
    proposed = spec.understood.category_positioning.proposed_candidates
    assert proposed
    assert proposed[0].category_path == "Pets > Pet Accessories > Bowls & Feeders"
    assert not can_confirm_selection([])

    path = proposed[0].category_path
    spec = confirm_categories(spec, [path])
    assert is_category_confirmation_complete(spec)
    print("validate_category_confirmation_gate: OK")


if __name__ == "__main__":
    main()
