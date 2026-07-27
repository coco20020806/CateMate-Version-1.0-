"""Collect execution outputs for verify and workbook assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


def make_storage_key(section_id: str, metric_id: str, table_id: str) -> str:
    return f"{section_id}:{metric_id}:{table_id}"


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
        storage_key = make_storage_key(section_id, metric_id, table_id)
        self.tables.append(
            {
                "table_id": table_id,
                "storage_key": storage_key,
                "run_id": run_id,
                "section_id": section_id,
                "module_id": module_id,
                "metric_id": metric_id,
                "table_kind": table_kind,
                "row_count": len(dataframe),
            }
        )
        self.dataframes[storage_key] = dataframe

    def merge(self, other: ExecutionResult) -> None:
        for item in other.tables:
            self.tables.append(item)
        self.dataframes.update(other.dataframes)
        self.errors.extend(other.errors)

    def primary_table(
        self,
        *,
        section_id: str,
        metric_id: str,
        table_id: str | None = None,
    ) -> pd.DataFrame | None:
        for item in self.tables:
            if item.get("section_id") != section_id or item.get("metric_id") != metric_id:
                continue
            if item.get("table_kind") != "primary":
                continue
            if table_id is not None and item.get("table_id") != table_id:
                continue
            storage_key = item.get("storage_key") or make_storage_key(
                section_id, metric_id, str(item.get("table_id", ""))
            )
            return self.dataframes.get(storage_key)
        return None
