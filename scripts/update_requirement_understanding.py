"""Update an existing RequirementUnderstandingSpec with user supplemental answers."""

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
from catemate.case_generation.context_loader import load_data_module_summaries, load_request_text
from catemate.core.paths import CONFIG_DIR, OUTPUTS_DIR, ensure_project_dirs
from catemate.understanding.schemas import RequirementUnderstandingSpec
from catemate.understanding.updater import RequirementUnderstandingUpdater


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update RequirementUnderstandingSpec JSON with user supplemental answer."
    )
    parser.add_argument(
        "--understanding-spec",
        type=Path,
        required=True,
        help="Path to existing requirement understanding JSON.",
    )
    parser.add_argument("--answer-text", type=str, default="", help="User supplemental answer text.")
    parser.add_argument(
        "--answer-file",
        type=Path,
        default=None,
        help="Path to txt/md file containing user answer.",
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
    args = parser.parse_args()

    ensure_project_dirs()

    if not args.understanding_spec.exists():
        print(f"understanding-spec not found: {args.understanding_spec}", file=sys.stderr)
        return 2

    try:
        answer_text = load_request_text(args.answer_text, args.answer_file)
        module_summaries = load_data_module_summaries(args.data_modules_dir)
        existing = RequirementUnderstandingSpec.model_validate(
            json.loads(args.understanding_spec.read_text(encoding="utf-8"))
        )
    except Exception as exc:
        print(f"Input/context error: {exc}", file=sys.stderr)
        return 2

    try:
        settings = AISettings.from_env()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    updater = RequirementUnderstandingUpdater(CateMateAIClient(settings))
    try:
        spec = updater.update(
            existing,
            answer_text,
            data_module_summaries=module_summaries,
        )
    except Exception as exc:
        print(f"Understanding update failed: {exc}", file=sys.stderr)
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output or (
        OUTPUTS_DIR / f"requirement_understanding_{existing.case_id}_{timestamp}.json"
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
    print(f"can_select_modules: {spec.readiness.can_select_modules}")
    print(f"assumptions: {len(spec.assumptions)}")
    print(f"clarifying_questions: {len(spec.clarifying_questions)}")
    print(f"user_answers: {len(spec.user_answers)}")
    print(f"metric_definitions: {spec.understood.metric_definitions}")
    print(f"analysis_intents: {[item.value for item in spec.understood.analysis_intents]}")
    print(f"output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
