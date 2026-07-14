"""Acceptance checks for Streamlit pipeline runtime (module cache + subprocess path)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_no_stale_generator_imports() -> None:
    pattern = re.compile(
        r"from\s+catemate\.case_generation\.generator\s+import\s+.*enrich_confirmation_templates"
    )
    offenders: list[str] = []
    for path in PROJECT_ROOT.rglob("*.py"):
        if path.parts[-1] == "verify_pipeline_runtime.py":
            continue
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    if offenders:
        raise AssertionError(f"stale generator imports found: {offenders}")


def check_fresh_import_surface() -> None:
    from catemate.case_generation.confirmation_enrichment import enrich_confirmation_templates
    from catemate.case_generation.generator import enrich_confirmation_templates as reexported

    assert enrich_confirmation_templates is reexported


def check_stale_cache_reproduction_and_subprocess_fix() -> None:
    import catemate.case_generation.generator as gen_mod

    if hasattr(gen_mod, "enrich_confirmation_templates"):
        delattr(gen_mod, "enrich_confirmation_templates")

    try:
        from catemate.case_generation.generator import enrich_confirmation_templates as _  # noqa: F401
    except ImportError:
        pass
    else:
        raise AssertionError("expected stale generator import to fail in simulation")

    from catemate.case_generation.confirmation_enrichment import enrich_confirmation_templates

    assert callable(enrich_confirmation_templates)

    from app.pipeline_runtime import run_pipeline_continue_from_manifest_subprocess

    manifest = (
        PROJECT_ROOT
        / "outputs"
        / "runs"
        / "cat_litter_box_ph_20260710_144051"
        / "pipeline_manifest_cat_litter_box_ph_20260710_144051.json"
    )
    if not manifest.exists():
        raise AssertionError(f"missing fixture manifest: {manifest}")

    result = run_pipeline_continue_from_manifest_subprocess(manifest)
    if result.exit_code != 0:
        raise AssertionError(f"subprocess continue failed: {result.error_message}")
    if result.manifest is None or result.manifest.status != "workbook_generated":
        raise AssertionError(f"unexpected manifest status: {result.manifest and result.manifest.status}")


def check_streamlit_imports() -> None:
    import app.streamlit_dashboard  # noqa: F401


def main() -> int:
    checks = [
        ("no stale generator imports in repo", check_no_stale_generator_imports),
        ("fresh import surface", check_fresh_import_surface),
        ("stale-cache simulation + subprocess continue", check_stale_cache_reproduction_and_subprocess_fix),
        ("streamlit dashboard imports", check_streamlit_imports),
    ]
    for name, fn in checks:
        print(f"[RUN] {name}")
        fn()
        print(f"[PASS] {name}")
    print("ALL ACCEPTANCE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
