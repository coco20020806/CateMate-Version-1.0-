from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_modules.top_shop import ScopedFrame, compute


def test_top_shop_ranking() -> None:
    rows = []
    for i in range(25):
        rows.append(
            {
                "shop_id": f"shop_{i}",
                "grass_region": "SG",
                "mtd_adgmv_usd(SUM)": float(i),
                "mtd_ado(SUM)": float(i) / 10,
            }
        )
    frame = ScopedFrame(data=pd.DataFrame(rows), scope_label="test", scope_spec={})
    result = compute(frame)["top_shop_ranking"]

    assert len(result) == 20
    assert result.iloc[0]["shop_id"] == "shop_24"
    assert result.attrs["top_n"] == 20
