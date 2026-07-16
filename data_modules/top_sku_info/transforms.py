"""top_sku_info — no derived tables; rankings are final deliverables."""

from __future__ import annotations

from typing import Any

import pandas as pd


def transform(
    primary_tables: dict[str, pd.DataFrame],
    derived_specs: list[dict[str, Any]] | None = None,
) -> dict[str, pd.DataFrame]:
    _ = primary_tables, derived_specs
    return {}
