from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_modules.top_listing import ScopedFrame, compute


def test_top_listing_ranking() -> None:
    rows = []
    for i in range(25):
        rows.append(
            {
                "item_name": f"item_{i}",
                "current_adgmv(RAW)": float(i),
                "current_ado(RAW)": float(i) / 5,
            }
        )
    frame = ScopedFrame(data=pd.DataFrame(rows), scope_label="test", scope_spec={})
    result = compute(frame)["top_listing_ranking"]

    assert len(result) == 20
    assert result.iloc[0]["item_name"] == "item_24"
