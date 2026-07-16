"""Tests for scope filters."""

from __future__ import annotations

import pandas as pd

from catemate.scope.filters import apply_scope_filters
from catemate.scope.schemas import ScopeSpec


def test_apply_site_filter() -> None:
    df = pd.DataFrame(
        {
            "grass_region": ["SG", "VN", "SG"],
            "gmv_usd": [1, 2, 3],
        }
    )
    spec = ScopeSpec(target_sites=["SG"])
    filtered = apply_scope_filters(df, spec)
    assert len(filtered) == 2
    assert set(filtered["grass_region"]) == {"SG"}
