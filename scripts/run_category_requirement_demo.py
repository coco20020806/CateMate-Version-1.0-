"""Run the first CateMate category requirement workbook demo."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.core.paths import OUTPUTS_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR, ensure_project_dirs
from catemate.modules.category_analysis_data_requirement import build_requirement_workbook
from catemate.schemas.category_requirement import RequirementContext


def main() -> None:
    ensure_project_dirs()
    context = RequirementContext(
        original_request=(
            "HKCB Collectible Category Insight: 收集 H&C 类目市场资讯，以吸引潜在卖家入驻，"
            "并为品牌卖家提供各站点市场机会及类目布局指引。重点关注 Action Figures 和 Movies & Anime。"
        ),
        target_category_text="Hobbies & Collections / Collectible Items / Action Figures / Movies & Anime",
        business_background="对外招商与品牌卖家沟通，需要注意脱敏和口径可追溯。",
        delivery_audience="潜在卖家与品牌卖家",
        delivery_format="Excel 数据需求集合；后续可转 PPT",
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUTS_DIR / f"category_analysis_data_requirement_{timestamp}.xlsx"
    result = build_requirement_workbook(
        context=context,
        raw_data_dir=RAW_DATA_DIR,
        processed_data_dir=PROCESSED_DATA_DIR,
        output_path=output_path,
    )
    print(f"Generated: {result}")


if __name__ == "__main__":
    main()
