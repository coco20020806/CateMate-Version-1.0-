"""Tests for ExecutionResult storage keys."""

from __future__ import annotations

import pandas as pd

from catemate.execution.result_collector import ExecutionResult, make_storage_key


def test_same_table_id_different_sections_do_not_overwrite() -> None:
    result = ExecutionResult()
    result.add_table(
        table_id="gmv_by_site_month",
        dataframe=pd.DataFrame({"gmv_usd": [1]}),
        section_id="s_subset",
        metric_id="gmv",
        table_kind="primary",
    )
    result.add_table(
        table_id="gmv_by_site_month",
        dataframe=pd.DataFrame({"gmv_usd": [999]}),
        section_id="s_parent",
        metric_id="gmv",
        table_kind="primary",
    )
    assert len(result.dataframes) == 2
    subset_key = make_storage_key("s_subset", "gmv", "gmv_by_site_month")
    parent_key = make_storage_key("s_parent", "gmv", "gmv_by_site_month")
    assert result.dataframes[subset_key]["gmv_usd"].iloc[0] == 1
    assert result.dataframes[parent_key]["gmv_usd"].iloc[0] == 999
