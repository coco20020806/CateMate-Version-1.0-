"""CLI: ingest rawdata from user-supplied file path."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.data.rawdata_ingest import ingest_rawdata_from_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest rawdata Excel from local path.")
    parser.add_argument("--path", required=True, help="Full path to source Excel file.")
    parser.add_argument("--grain", required=True, choices=["category", "shop", "item"])
    parser.add_argument("--table-id", required=True, help="Catalog table_id to mark available.")
    parser.add_argument("--skip-preprocess", action="store_true")
    args = parser.parse_args()

    result = ingest_rawdata_from_path(
        source_path=args.path,
        grain=args.grain,
        table_id=args.table_id,
        run_preprocess=not args.skip_preprocess,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
