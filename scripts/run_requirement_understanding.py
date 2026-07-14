"""Run Requirement Understanding Layer v1 for a natural-language request."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.ai.client import CateMateAIClient
from catemate.ai.settings import AISettings
from catemate.case_generation.context_loader import (
    load_category_tree_l3_candidates,
    load_data_module_summaries,
    load_request_text,
    safe_slug,
)
from catemate.core.paths import CONFIG_DIR, OUTPUTS_DIR, ensure_project_dirs
from catemate.understanding.generator import RequirementUnderstandingGenerator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate RequirementUnderstandingSpec JSON from natural-language request."
    )
    parser.add_argument("--request-text", type=str, default="", help="Raw user request text.")
    parser.add_argument(
        "--request-file",
        type=Path,
        default=None,
        help="Path to txt/md file containing request text.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON path.",
    )
    parser.add_argument(
        "--data-modules-dir",
        type=Path,
        default=CONFIG_DIR / "data_modules",
        help="Directory of active data module YAML files.",
    )
    parser.add_argument(
        "--category-tree-lookup",
        type=Path,
        default=PROJECT_ROOT / "CateMate_processeddata" / "sph_category_tree_lookup.csv",
        help="Path to category tree lookup CSV (L1/L2/L3 candidates).",
    )
    args = parser.parse_args()

    ensure_project_dirs()

    try:
        request_text = load_request_text(args.request_text, args.request_file)
        module_summaries = load_data_module_summaries(args.data_modules_dir)
        category_tree_candidates = load_category_tree_l3_candidates(args.category_tree_lookup)
    except Exception as exc:
        print(f"Input/context error: {exc}", file=sys.stderr)
        return 2

    try:
        settings = AISettings.from_env()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    generator = RequirementUnderstandingGenerator(CateMateAIClient(settings))
    try:
        spec = generator.generate(
            request_text=request_text,
            data_module_summaries=module_summaries,
            category_tree_candidates=category_tree_candidates,
        )
    except Exception as exc:
        print(f"Understanding generation failed: {exc}", file=sys.stderr)
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_case_id = safe_slug(spec.case_id, timestamp=timestamp)
    output_path = args.output or (
        OUTPUTS_DIR / f"requirement_understanding_{safe_case_id}_{timestamp}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(spec.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"provider: {settings.provider}")
    print(f"model: {settings.model}")
    print(f"case_id: {spec.case_id}")
    print(f"status: {spec.status.value}")
    print(f"target_sites: {spec.understood.target_sites}")
    print(f"target_category_text: {spec.understood.target_category_text}")
    print(f"inferred_category: {spec.understood.inferred_category}")
    print(f"analysis_intents: {[item.value for item in spec.understood.analysis_intents]}")
    print(f"assumptions: {len(spec.assumptions)}")
    print(f"clarifying_questions: {len(spec.clarifying_questions)}")
    print(f"can_select_modules: {spec.readiness.can_select_modules}")
    print(f"output: {output_path}")

    if spec.status.value in {"needs_minimum_context", "out_of_scope"}:
        print("blocking_reasons:")
        for reason in spec.readiness.blocking_reasons:
            print(f"  - {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
