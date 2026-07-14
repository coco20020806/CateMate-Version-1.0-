"""Generate a draft case config YAML from natural-language request text."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from catemate.ai.client import CateMateAIClient
from catemate.ai.settings import AISettings
from catemate.case_generation.context_loader import (
    ensure_case_id,
    load_data_module_summaries,
    load_reference_case_summaries,
    load_request_text,
    safe_slug,
    save_case_config_yaml,
)
from catemate.case_generation.generator import CaseConfigGenerator
from catemate.core.paths import CONFIG_DIR, OUTPUTS_DIR, ensure_project_dirs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate CategoryAnalysisCaseConfig draft YAML from natural-language request."
    )
    parser.add_argument("--request-text", type=str, default="", help="Raw user request text.")
    parser.add_argument(
        "--request-file",
        type=Path,
        default=None,
        help="Path to txt/md file containing request text. If set, it overrides --request-text.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output YAML path. Defaults to outputs/generated_case_config_<case_id>_<timestamp>.yaml",
    )
    parser.add_argument(
        "--reference-cases-dir",
        type=Path,
        default=CONFIG_DIR / "cases",
        help="Directory of reference case YAML files.",
    )
    parser.add_argument(
        "--data-modules-dir",
        type=Path,
        default=CONFIG_DIR / "data_modules",
        help="Directory of data module YAML files.",
    )
    args = parser.parse_args()

    ensure_project_dirs()

    try:
        request_text = load_request_text(args.request_text, args.request_file)
    except Exception as exc:
        print(f"Request input error: {exc}", file=sys.stderr)
        return 2

    try:
        reference_cases = load_reference_case_summaries(args.reference_cases_dir)
        module_summaries = load_data_module_summaries(args.data_modules_dir)
    except Exception as exc:
        print(f"Context load error: {exc}", file=sys.stderr)
        return 2

    try:
        settings = AISettings.from_env()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    generator = CaseConfigGenerator(CateMateAIClient(settings))
    try:
        case_config = generator.generate(
            request_text=request_text,
            reference_case_configs=reference_cases,
            data_module_summaries=module_summaries,
        )
    except Exception as exc:
        print(f"Generation failed: {exc}", file=sys.stderr)
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    case_config = ensure_case_id(case_config, timestamp=timestamp)
    safe_case_id = safe_slug(case_config.case_id, timestamp=timestamp)
    output_path = args.output or (OUTPUTS_DIR / f"generated_case_config_{safe_case_id}_{timestamp}.yaml")

    try:
        save_case_config_yaml(case_config, output_path)
    except Exception as exc:
        print(f"Failed to save YAML: {exc}", file=sys.stderr)
        return 1

    print(f"provider: {settings.provider}")
    print(f"model: {settings.model}")
    print(f"case_id: {case_config.case_id}")
    print(f"project_name: {case_config.project_name}")
    print(f"target_category_text: {case_config.target_category_text}")
    print(f"target_sites: {case_config.target_sites}")
    print(f"output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
