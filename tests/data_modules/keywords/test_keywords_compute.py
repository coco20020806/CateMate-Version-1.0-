from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_modules.keywords import ScopedFrame, compute


def test_top_keywords() -> None:
    rows = []
    for i in range(25):
        rows.append(
            {
                "keyword": f"kw_{i}",
                "current_daily_item_click(SUM)": float(i),
            }
        )
    frame = ScopedFrame(data=pd.DataFrame(rows), scope_label="test", scope_spec={})
    result = compute(frame)["top_keywords"]

    assert len(result) == 20
    assert result.iloc[0]["keyword"] == "kw_24"
    assert result.iloc[0]["current_daily_item_click(SUM)"] == 24.0
