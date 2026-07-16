"""Pilot: Scope + if_related + top_sku_info for Sub-L3 concepts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.scope.concept_schemas import RelatedConceptPack
from catemate.scope.executor import execute_scope
from catemate.scope.schemas import ScopeSpec
from data_modules.top_sku_info import ComputeParams, compute

DEFAULT_PACK = RelatedConceptPack(
    concept_id="smart_pet_bowl",
    display_name="智能宠物碗",
    parent_l3="Bowls & Feeders",
    scope_note="宽定义：含智能饮水器/自动喂食器",
    smart_signals=[
        "smart",
        "automatic",
        "auto",
        "electric",
        "wireless",
        "sensor",
        "fountain",
        "dispenser",
        "feeder",
        "智能",
        "自动",
    ],
    pet_context=["pet", "cat", "dog", "猫", "狗"],
    boost_terms=["fountain", "dispenser", "feeder", "filter", "circulat"],
    exclude_terms=[
        "chicken",
        "poultry",
        "quail",
        "bird",
        "slow feed",
        "maze",
        "anti.?gulping",
        "replacement",
    ],
    min_score=0.55,
)


def _load_pack(path: Path | None) -> RelatedConceptPack:
    if path is None:
        return DEFAULT_PACK
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RelatedConceptPack.model_validate(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Scope + if_related + top_sku_info pilot.")
    parser.add_argument("--site", default="PH", help="Target site code, e.g. PH")
    parser.add_argument("--category-l1", default="Pets")
    parser.add_argument("--category-l2", default="Pet Accessories")
    parser.add_argument("--category-l3", default="Bowls & Feeders")
    parser.add_argument("--table-id", default="item_l3_category_csv")
    parser.add_argument("--concept-pack-json", type=Path, default=None)
    parser.add_argument("--min-score", type=float, default=0.55)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "if_related_pilot",
    )
    args = parser.parse_args()

    pack = _load_pack(args.concept_pack_json)
    scope_label = f"{args.site} / {args.category_l3} / {pack.display_name}"
    spec = ScopeSpec(
        grain="item",
        table_id=args.table_id,
        target_sites=[args.site],
        category_l1=args.category_l1,
        category_l2=args.category_l2,
        category_l3=args.category_l3,
        scope_label=scope_label,
        related_concept_pack=pack,
        related_min_score=args.min_score,
    )

    frame = execute_scope(spec)
    input_rows = len(frame.data)
    unique_titles = frame.data["item_name"].nunique() if "item_name" in frame.data.columns else 0

    params = ComputeParams(top_n=args.top_n, sort_by="both")
    tables = compute(params, frame)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "scope_label": frame.scope_label,
        "concept_id": pack.concept_id,
        "display_name": pack.display_name,
        "input_rows_after_if_related": input_rows,
        "unique_item_names": int(unique_titles),
        "output_tables": list(tables.keys()),
        "top_skus": {},
    }
    for table_id, df in tables.items():
        preview = df.head(args.top_n)
        summary["top_skus"][table_id] = preview[
            [col for col in ["grass_region", "grass_month", "rank", "item_name", "orders", "gmv_usd"] if col in preview.columns]
        ].to_dict(orient="records")

    out_path = args.output_dir / f"if_related_pilot_{pack.concept_id}_{args.site}.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
