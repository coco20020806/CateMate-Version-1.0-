"""Collect execution outputs for verify and workbook assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ExecutionResult:
    tables: list[dict[str, Any]] = field(default_factory=list)
    dataframes: dict[str, pd.DataFrame] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def add_table(
        self,
        *,
        table_id: str,
        dataframe: pd.DataFrame,
        run_id: str = "",
        section_id: str = "",
        module_id: str = "",
        metric_id: str = "",
        table_kind: str = "primary",
    ) -> None:
        self.tables.append(
            {
                "table_id": table_id,
                "run_id": run_id,
                "section_id": section_id,
                "module_id": module_id,
                "metric_id": metric_id,
                "table_kind": table_kind,
                "row_count": len(dataframe),
            }
        )
        self.dataframes[table_id] = dataframe

    def merge(self, other: ExecutionResult) -> None:
        for item in other.tables:
            self.tables.append(item)
        self.dataframes.update(other.dataframes)
        self.errors.extend(other.errors)
