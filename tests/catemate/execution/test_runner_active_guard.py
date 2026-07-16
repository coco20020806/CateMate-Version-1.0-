"""Tests for execution runner active module guard."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from catemate.execution.runner import _run_module


def _draft_run(module_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        module_id=module_id,
        grain="category",
        table_id="dashboard_history",
        target_sites=["SG"],
        category_l1="Pets",
        category_l2="Pet Accessories",
        category_l3="Bowls & Feeders",
        scope_label="SG / Bowls",
        related_concept_pack=None,
        related_min_score=0.55,
        metric_id="gmv",
    )


def test_draft_module_rejected_before_scope() -> None:
    with pytest.raises(ValueError, match="not active"):
        _run_module(_draft_run("daily_cncb_performance"))
