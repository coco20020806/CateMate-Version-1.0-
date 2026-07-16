from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_modules.price_tier_distribution import ScopedFrame, compute


def test_price_tier_by_site() -> None:
    data = pd.DataFrame(
        {
            "Price_Range_USD": ["01_[0,1)", "01_[0,1)", "02_[1,5)"],
            "grass_region": ["SG", "SG", "MY"],
            "ADO": [10, 5, 8],
            "ADG": [100, 50, 80],
        }
    )
    frame = ScopedFrame(data=data, scope_label="test", scope_spec={})
    result = compute(frame)["price_tier_by_site"]

    sg = result[
        (result["Price_Range_USD"] == "01_[0,1)") & (result["grass_region"] == "SG")
    ].iloc[0]
    assert sg["ADO"] == 15
    assert sg["ADG"] == 150
