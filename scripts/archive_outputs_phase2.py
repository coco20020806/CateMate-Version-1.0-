"""Phase 2: move flat outputs/ files into runs/ and _legacy/ with rollback map."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = PROJECT_ROOT / "outputs"
RUNS = OUTPUTS / "runs"
LEGACY = OUTPUTS / "_legacy"
ORPHANS = LEGACY / "orphans"
SUPERSEDED = LEGACY / "superseded"
ROLLBACK = OUTPUTS / "rollback_map.json"

MANIFEST_KEYS = [
    "case_config_path",
    "understanding_spec_path",
    "module_selection_plan_path",
    "planning_spec_path",
    "requirement_workbook_path",
    "ppt_ready_workbook_path",
    "html_preview_path",
]

SKIP_NAMES = {"rollback_map.json", "_cleanup_inventory.json", "_cleanup_inventory.md"}


def _load_inventory() -> dict:
    path = OUTPUTS / "_cleanup_inventory.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"runs": [], "orphans": []}


def _rewrite_manifest_paths(manifest_path: Path, moves: dict[str, str]) -> None:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed = False
    for key in MANIFEST_KEYS:
        raw = data.get(key)
        if not raw:
            continue
        resolved = str(Path(raw).resolve())
        if resolved in moves:
            data[key] = moves[resolved]
            changed = True
    if changed:
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _move_file(src: Path, dest: Path, moves: dict[str, str]) -> None:
    if not src.exists() or not src.is_file():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        index = 2
        while dest.exists():
            dest = dest.with_name(f"{stem}__dup{index}{suffix}")
            index += 1
    shutil.move(str(src), str(dest))
    moves[str(src.resolve())] = str(dest.resolve())


def archive_runs(inventory: dict, moves: dict[str, str]) -> list[dict]:
    actions: list[dict] = []
    for run in inventory.get("runs", []):
        run_id = run["run_id"]
        dest_dir = RUNS / run_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        keep_ppt = run.get("keep_latest_ppt")
        keep_html = run.get("keep_latest_html")
        for name in run.get("files", []):
            src = OUTPUTS / name
            if not src.exists():
                continue
            if name in run.get("archive_older_ppt", []) or name in run.get("archive_older_html", []):
                target = SUPERSEDED / name
            else:
                target = dest_dir / name
            _move_file(src, target, moves)
            actions.append({"type": "run_file", "run_id": run_id, "from": name, "to": str(target.relative_to(OUTPUTS))})
        manifest_in_run = dest_dir / run["manifest"]
        if manifest_in_run.exists():
            _rewrite_manifest_paths(manifest_in_run, moves)
    return actions


def archive_orphans(inventory: dict, moves: dict[str, str]) -> list[dict]:
    actions: list[dict] = []
    for row in inventory.get("orphans", []):
        name = row["file"]
        if name in SKIP_NAMES:
            continue
        src = OUTPUTS / name
        if not src.exists():
            continue
        target = ORPHANS / name
        _move_file(src, target, moves)
        actions.append({"type": "orphan", "from": name, "to": str(target.relative_to(OUTPUTS))})
    return actions


def archive_stragglers(moves: dict[str, str]) -> list[dict]:
    """Move any remaining flat files (except inventory/rollback) into orphans."""
    actions: list[dict] = []
    for src in OUTPUTS.iterdir():
        if not src.is_file():
            continue
        if src.name.startswith("_cleanup_") or src.name == "rollback_map.json":
            continue
        target = ORPHANS / src.name
        _move_file(src, target, moves)
        actions.append({"type": "straggler", "from": src.name, "to": str(target.relative_to(OUTPUTS))})
    return actions


def main() -> int:
    inventory = _load_inventory()
    RUNS.mkdir(parents=True, exist_ok=True)
    ORPHANS.mkdir(parents=True, exist_ok=True)
    SUPERSEDED.mkdir(parents=True, exist_ok=True)

    moves: dict[str, str] = {}
    actions: list[dict] = []
    actions.extend(archive_runs(inventory, moves))
    actions.extend(archive_orphans(inventory, moves))
    actions.extend(archive_stragglers(moves))

    rollback = {
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "moves": moves,
        "actions": actions,
        "note": "To rollback: for each entry in moves, shutil.move(new_path, old_path) and restore manifest JSON from git/backup if needed.",
    }
    ROLLBACK.write_text(json.dumps(rollback, ensure_ascii=False, indent=2), encoding="utf-8")

    remaining_files = [p.name for p in OUTPUTS.iterdir() if p.is_file() and not p.name.startswith("_cleanup_")]
    print(f"Archived {len(actions)} file moves.")
    print(f"Rollback map: {ROLLBACK}")
    print(f"Runs dir count: {len(list(RUNS.iterdir()))}")
    print(f"Remaining flat files (expected cleanup meta only): {remaining_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
