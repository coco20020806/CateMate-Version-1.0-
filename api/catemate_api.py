"""FastAPI bridge that exposes the real CateMate Python pipeline as REST endpoints.

Designed to be called by the CateMate-Workbench Express proxy or directly.
All long-running operations are executed in background tasks and tracked via task IDs.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Bootstrap: ensure project root is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from catemate.core.paths import (
    CONFIG_DIR,
    OUTPUTS_DIR,
    PROCESSED_DATA_DIR,
    PROJECT_ROOT as CATEMATE_ROOT,
    RAW_DATA_DIR,
    RAWDATA_GRAIN_DIRS,
)
from catemate.pipeline.manifest import (
    PipelineManifest,
    iter_pipeline_manifest_paths,
    load_pipeline_manifest,
    resolve_manifest_path,
    update_and_save_manifest,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="CateMate API Bridge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory task store for async operations
# ---------------------------------------------------------------------------

class TaskInfo(BaseModel):
    id: str
    status: str = "pending"  # pending | running | completed | failed
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = ""
    completed_at: str | None = None

_tasks: dict[str, TaskInfo] = {}


def _new_task() -> TaskInfo:
    task = TaskInfo(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _tasks[task.id] = task
    return task


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _manifest_to_run_id(manifest_path: Path) -> str:
    """Derive a stable run ID from a manifest path (stem)."""
    return manifest_path.stem.replace("pipeline_manifest_", "")


def _find_manifest_by_run_id(run_id: str) -> Path | None:
    for p in iter_pipeline_manifest_paths(OUTPUTS_DIR):
        if _manifest_to_run_id(p) == run_id:
            return p
    return None


def _manifest_to_dict(manifest: PipelineManifest, manifest_path: Path) -> dict[str, Any]:
    """Convert manifest to a JSON-safe dict matching the frontend Run schema."""
    run_id = _manifest_to_run_id(manifest_path)

    understanding = _load_json_artifact(manifest, "understanding_spec_path")
    clarifying_questions = None
    if understanding:
        raw_questions = understanding.get("clarifying_questions", [])
        clarifying_questions = [
            {
                "id": q.get("question_id", q.get("id", "")),
                "question": q.get("question", ""),
                "type": q.get("expected_answer_type", q.get("type", "text")),
                "answer": _get_answer_for_question(understanding, q.get("question_id", q.get("id", ""))),
                "skipped": _is_question_skipped(understanding, q.get("question_id", q.get("id", ""))),
                "reason": q.get("reason", ""),
                "defaultAssumption": q.get("default_assumption", ""),
                "questionCategory": q.get("question_category", ""),
                "rawdataGrain": q.get("rawdata_grain"),
                "rawdataTableId": q.get("rawdata_table_id"),
                "clarificationKind": q.get("clarification_kind"),
            }
            for q in raw_questions
        ]

    solve_progress = _build_solve_progress(manifest)
    deliverables = _build_deliverables(manifest, manifest_path)

    categories = []
    if understanding:
        understood = understanding.get("understood", {}) or {}
        positioning = understood.get("category_positioning", {}) or {}
        proposed = list(positioning.get("proposed_candidates") or [])
        confirmed = list(positioning.get("confirmed_candidates") or [])
        confirmed_keys = {
            str(c.get("category_path") or "").strip()
            for c in confirmed
            if isinstance(c, dict) and str(c.get("category_path") or "").strip()
        }

        def _candidate_row(c: dict[str, Any], *, index: int, selected: bool) -> dict[str, Any]:
            key = str(c.get("category_path") or "").strip() or f"cat_{index}"
            name = (
                str(c.get("category_name") or "").strip()
                or str(c.get("l3") or "").strip()
                or key
            )
            level = str(c.get("level") or "").strip()
            if not level:
                if c.get("l3"):
                    level = "L3"
                elif c.get("l2"):
                    level = "L2"
                elif c.get("l1"):
                    level = "L1"
            return {
                "id": key,
                "name": name,
                "level": level,
                "site": c.get("site", ""),
                "positioning": c.get("reason", ""),
                "confidence": c.get("confidence", ""),
                "selected": selected,
            }

        seen_keys: set[str] = set()
        for i, c in enumerate(proposed):
            if not isinstance(c, dict):
                continue
            row = _candidate_row(c, index=i, selected=str(c.get("category_path") or "").strip() in confirmed_keys)
            categories.append(row)
            seen_keys.add(row["id"])

        # After confirmation, proposed may be empty — still surface confirmed candidates.
        for i, c in enumerate(confirmed):
            if not isinstance(c, dict):
                continue
            key = str(c.get("category_path") or "").strip() or f"confirmed_{i}"
            if key in seen_keys:
                continue
            categories.append(_candidate_row(c, index=1000 + i, selected=True))
            seen_keys.add(key)

    understanding_summary = None
    if understanding:
        understood = understanding.get("understood", {}) or {}
        sites = [str(s).strip() for s in (understood.get("target_sites") or []) if str(s).strip()]
        intents = understood.get("analysis_intents") or []
        intent_texts: list[str] = []
        for item in intents:
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, dict):
                text = str(item.get("value") or item.get("name") or item).strip()
            else:
                text = str(getattr(item, "value", item)).strip()
            if text:
                intent_texts.append(text)

        assumptions = [
            str(a.get("content") or "").strip()
            for a in (understanding.get("assumptions") or [])
            if isinstance(a, dict) and str(a.get("content") or "").strip()
        ]
        risks = [
            str(u.get("description") or "").strip()
            for u in (understanding.get("uncertainties") or [])
            if isinstance(u, dict) and str(u.get("description") or "").strip()
        ]

        pack = understood.get("related_concept_pack") or {}
        concept_pack: list[str] = []
        if isinstance(pack, dict):
            for key in ("smart_signals", "boost_terms", "pet_context"):
                for term in pack.get(key) or []:
                    text = str(term).strip()
                    if text and text not in concept_pack:
                        concept_pack.append(text)

        understanding_summary = {
            "site": ", ".join(sites) if sites else "全部站点",
            "intent": ", ".join(intent_texts),
            "timeRange": understood.get("time_range", "") or "",
            "categories": categories,
            "assumptions": assumptions,
            "risks": risks,
            "conceptPack": concept_pack,
        }

    return {
        "id": run_id,
        "caseId": manifest.case_id,
        "status": manifest.status,
        "planningMode": manifest.planning_mode,
        "requirementText": manifest.request_text,
        "site": understanding_summary.get("site") if understanding_summary else None,
        "category": None,
        "errorMessage": manifest.error_message,
        "createdAt": manifest.created_at or manifest.timestamp,
        "updatedAt": None,
        "understanding": understanding_summary,
        "clarifyingQuestions": clarifying_questions,
        "deliverables": deliverables,
        "solveProgress": solve_progress,
        "manifestPath": str(manifest_path),
    }


def _get_answer_for_question(understanding: dict, qid: str) -> str | None:
    for a in understanding.get("user_answers", []):
        if a.get("question_id") == qid:
            ans = a.get("answer", "")
            if ans == "__SKIPPED__":
                return None
            return ans
    return None


def _is_question_skipped(understanding: dict, qid: str) -> bool:
    for a in understanding.get("user_answers", []):
        if a.get("question_id") == qid:
            return a.get("answer") == "__SKIPPED__"
    return False


def _load_json_artifact(manifest: PipelineManifest, attr_name: str) -> dict | None:
    raw_path = getattr(manifest, attr_name, None)
    resolved = resolve_manifest_path(CATEMATE_ROOT, raw_path)
    if resolved and resolved.exists():
        try:
            return json.loads(resolved.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _build_solve_progress(manifest: PipelineManifest) -> dict | None:
    status = manifest.status
    phase_order = ["blueprint", "plan", "catalog", "execute", "verify", "done"]
    if status in ("awaiting_category_confirmation", "category_confirmed",
                   "awaiting_clarification", "clarification_completed"):
        return None

    solve_state = _load_json_artifact(manifest, "solve_loop_state_path")
    if solve_state:
        phase = solve_state.get("phase", "blueprint")
        completed = []
        for p in phase_order:
            if p == phase:
                break
            completed.append(p)
        pct = int(len(completed) / len(phase_order) * 100)
        return {"phase": phase, "completedPhases": completed, "percentComplete": pct, "message": f"Phase: {phase}"}

    if manifest.data_workbook_path:
        return {"phase": "done", "completedPhases": phase_order, "percentComplete": 100, "message": "Data Workbook generated"}

    return None


def _build_deliverables(manifest: PipelineManifest, manifest_path: Path) -> dict:
    run_id = _manifest_to_run_id(manifest_path)

    def _ref(attr: str, kind: str) -> dict:
        raw = getattr(manifest, attr, None)
        resolved = resolve_manifest_path(CATEMATE_ROOT, raw)
        if resolved and resolved.exists():
            return {"status": "ready", "downloadUrl": f"/api/files/{resolved.relative_to(CATEMATE_ROOT)}", "generatedAt": _utc_now()}
        return {"status": "not_started"}

    return {
        "workbook": _ref("data_workbook_path", "xlsx"),
        "brief": _ref("conclusion_brief_path", "md"),
        "htmlReport": _ref("html_report_path", "html"),
        "printReport": _ref("print_report_path", "html"),
    }


def _safe_relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(CATEMATE_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _processed_config_by_table_id() -> dict[str, dict[str, Any]]:
    payload = _load_yaml_dict(CONFIG_DIR / "processed_data_sources.yaml")
    result: dict[str, dict[str, Any]] = {}
    for entry in payload.get("tables") or []:
        if isinstance(entry, dict) and entry.get("table_id"):
            result[str(entry["table_id"])] = entry
    return result


def _processed_manifest_by_table_id() -> dict[str, dict[str, Any]]:
    payload = _load_yaml_dict(PROCESSED_DATA_DIR / "processed_manifest.yaml")
    result: dict[str, dict[str, Any]] = {}
    for entry in payload.get("tables") or []:
        if isinstance(entry, dict) and entry.get("table_id"):
            result[str(entry["table_id"])] = entry
    return result


def _module_usage_by_table_id() -> dict[str, list[str]]:
    usage: dict[str, set[str]] = {}
    import yaml

    for contract_path in (CATEMATE_ROOT / "data_modules").glob("*/contract.yaml"):
        try:
            contract = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if not isinstance(contract, dict):
            continue
        module_id = str(contract.get("module_id") or contract_path.parent.name)
        module_name = str(contract.get("module_name") or module_id)
        label = module_name if module_name == module_id else f"{module_name} ({module_id})"
        bindings = contract.get("source_bindings") or {}
        by_grain = bindings.get("by_grain") or {}
        if not isinstance(by_grain, dict):
            continue
        for grain_info in by_grain.values():
            if not isinstance(grain_info, dict):
                continue
            table_ids = []
            default_table_id = str(grain_info.get("default_table_id") or "").strip()
            if default_table_id:
                table_ids.append(default_table_id)
            table_ids.extend(str(item).strip() for item in grain_info.get("candidates") or [])
            for table_id in table_ids:
                if table_id:
                    usage.setdefault(table_id, set()).add(label)
    return {table_id: sorted(labels) for table_id, labels in usage.items()}


def _raw_source_exists(
    *,
    grain: str,
    table_id: str,
    catalog_entry: dict[str, Any],
    processed_config: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    file_path = str(catalog_entry.get("file_path") or catalog_entry.get("path") or "").strip()
    if file_path:
        resolved = resolve_manifest_path(CATEMATE_ROOT, file_path)
        if resolved and resolved.exists():
            return True, _safe_relative_path(resolved)

    resolution_mode = str(catalog_entry.get("resolution_mode") or "").strip()
    grain_dir = RAWDATA_GRAIN_DIRS.get(grain)
    if resolution_mode == "category_folder" and grain_dir and grain_dir.exists():
        has_files = any(path.is_file() for path in grain_dir.rglob("*"))
        return has_files, _safe_relative_path(grain_dir)

    if processed_config:
        keywords = [str(item).lower() for item in processed_config.get("source_workbook_keywords") or []]
        if keywords and RAW_DATA_DIR.exists():
            for path in RAW_DATA_DIR.glob("*"):
                if path.is_file() and all(keyword in path.name.lower() for keyword in keywords):
                    return True, _safe_relative_path(path)

    if grain_dir and grain_dir.exists():
        direct_matches = list(grain_dir.glob(f"{table_id}.*"))
        if direct_matches:
            return True, _safe_relative_path(direct_matches[0])

    return False, None


def _path_stats(path: Path) -> dict[str, Any]:
    file_count = 0
    folder_count = 0
    total_bytes = 0
    csv_file_count = 0
    csv_folder_count = 0
    csv_total_bytes = 0
    last_updated_ts: float | None = None
    csv_last_updated_ts: float | None = None
    if path.is_file():
        stat = path.stat()
        is_csv = path.suffix.lower() == ".csv"
        return {
            "fileCount": 1,
            "folderCount": 0,
            "totalBytes": stat.st_size,
            "csvFileCount": 1 if is_csv else 0,
            "csvFolderCount": 0,
            "csvTotalBytes": stat.st_size if is_csv else 0,
            "hasCsv": is_csv,
            "lastUpdated": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "csvLastUpdated": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat() if is_csv else None,
        }
    if path.is_dir():
        csv_dirs: set[Path] = set()
        for child in path.rglob("*"):
            try:
                stat = child.stat()
            except OSError:
                continue
            if child.is_dir():
                folder_count += 1
            elif child.is_file():
                file_count += 1
                total_bytes += stat.st_size
                if child.suffix.lower() == ".csv":
                    csv_file_count += 1
                    csv_total_bytes += stat.st_size
                    csv_dirs.add(child.parent)
                    csv_last_updated_ts = stat.st_mtime if csv_last_updated_ts is None else max(csv_last_updated_ts, stat.st_mtime)
            last_updated_ts = stat.st_mtime if last_updated_ts is None else max(last_updated_ts, stat.st_mtime)
        csv_folder_count = len(csv_dirs)
    return {
        "fileCount": file_count,
        "folderCount": folder_count,
        "totalBytes": total_bytes,
        "csvFileCount": csv_file_count,
        "csvFolderCount": csv_folder_count,
        "csvTotalBytes": csv_total_bytes,
        "hasCsv": csv_file_count > 0,
        "lastUpdated": datetime.fromtimestamp(last_updated_ts, timezone.utc).isoformat() if last_updated_ts else None,
        "csvLastUpdated": datetime.fromtimestamp(csv_last_updated_ts, timezone.utc).isoformat() if csv_last_updated_ts else None,
    }


def _rawdata_file_item(path: Path) -> dict[str, Any]:
    stats = _path_stats(path)
    return {
        "name": path.name,
        "path": _safe_relative_path(path),
        "kind": "file",
        **stats,
    }


def _rawdata_dir_item(path: Path, *, children: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    stats = _path_stats(path)
    return {
        "name": path.name,
        "path": _safe_relative_path(path),
        "kind": "directory",
        **stats,
        "children": children or [],
    }


def _rawdata_flat_group_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for child in sorted(path.rglob("*"), key=lambda item: str(item).lower()):
        if child.is_file() and child.suffix.lower() == ".csv":
            items.append(_rawdata_file_item(child))
        elif child.is_dir() and _path_stats(child)["hasCsv"]:
            items.append(_rawdata_dir_item(child))
    return items


def _rawdata_item_group_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    l1_items: list[dict[str, Any]] = []
    for l1 in sorted((item for item in path.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
        l2_items: list[dict[str, Any]] = []
        for l2 in sorted((item for item in l1.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
            l3_items: list[dict[str, Any]] = []
            for l3 in sorted((item for item in l2.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
                files = [
                    _rawdata_file_item(file)
                    for file in sorted(l3.rglob("*.csv"), key=lambda item: item.name.lower())
                    if file.is_file()
                ]
                if files:
                    l3_items.append(_rawdata_dir_item(l3, children=files))
            if l3_items:
                l2_items.append(_rawdata_dir_item(l2, children=l3_items))
        if l2_items:
            l1_items.append(_rawdata_dir_item(l1, children=l2_items))
    return l1_items


def _build_rawdata_tree() -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    for grain in ("category", "shop", "item"):
        path = RAWDATA_GRAIN_DIRS[grain]
        stats = _path_stats(path) if path.exists() else {
            "fileCount": 0,
            "folderCount": 0,
            "totalBytes": 0,
            "lastUpdated": None,
        }
        items = _rawdata_item_group_items(path) if grain == "item" else _rawdata_flat_group_items(path)
        groups.append({
            "grain": grain,
            "path": _safe_relative_path(path),
            "exists": path.exists(),
            **stats,
            "items": items,
        })
    return {"groups": groups}


def _build_datasource_catalog_response() -> dict[str, Any]:
    catalog_path = CONFIG_DIR / "rawdata_catalog.yaml"
    raw_catalog = _load_yaml_dict(catalog_path)
    tables = raw_catalog.get("tables") or []
    processed_config = _processed_config_by_table_id()
    processed_manifest = _processed_manifest_by_table_id()
    module_usage = _module_usage_by_table_id()
    rawdata_tree = _build_rawdata_tree()
    rawdata_groups = {group["grain"]: group for group in rawdata_tree["groups"]}

    entries: list[dict[str, Any]] = []
    summary = {
        "available": 0,
        "missing": 0,
        "partial": 0,
        "rawOnly": 0,
        "derivedOrFolder": 0,
        "processed": 0,
        "total": 0,
    }

    for catalog_entry in tables:
        if not isinstance(catalog_entry, dict):
            continue
        table_id = str(catalog_entry.get("table_id") or "").strip()
        grain = str(catalog_entry.get("grain") or "").strip()
        if not table_id or not grain:
            continue

        cfg = processed_config.get(table_id) or {}
        manifest = processed_manifest.get(table_id) or {}
        processed_rel = str(
            manifest.get("output_csv_relative")
            or cfg.get("output_csv")
            or ""
        ).strip()
        processed_path = PROCESSED_DATA_DIR / processed_rel if processed_rel else None
        processed_exists = bool(processed_path and processed_path.exists())
        has_manifest_stats = manifest.get("row_count") is not None and manifest.get("column_count") is not None
        raw_exists, raw_path = _raw_source_exists(
            grain=grain,
            table_id=table_id,
            catalog_entry=catalog_entry,
            processed_config=cfg,
        )
        rawdata_group = rawdata_groups.get(grain) or {}
        grain_dir = RAWDATA_GRAIN_DIRS.get(grain)
        rawdata_file_count = int(rawdata_group.get("fileCount") or 0)
        rawdata_folder_count = int(rawdata_group.get("folderCount") or 0)
        rawdata_csv_file_count = int(rawdata_group.get("csvFileCount") or 0)
        rawdata_csv_folder_count = int(rawdata_group.get("csvFolderCount") or 0)
        rawdata_exists = bool(rawdata_group.get("exists")) and (rawdata_file_count > 0 or rawdata_folder_count > 0)
        rawdata_has_csv = bool(rawdata_group.get("hasCsv"))
        rawdata_path = _safe_relative_path(grain_dir) if grain_dir else raw_path
        resolution_mode = str(catalog_entry.get("resolution_mode") or "").strip() or None
        declared_status = str(catalog_entry.get("status") or "missing").strip()

        if resolution_mode == "category_folder":
            status = "derived_or_folder" if raw_exists else "missing"
        elif processed_exists and not has_manifest_stats:
            status = "partial"
        elif declared_status == "available" and (raw_exists or processed_exists):
            status = "available"
        elif declared_status == "missing" and processed_exists:
            status = "partial"
        elif raw_exists and not processed_exists:
            status = "raw_only"
        else:
            status = "missing"

        missing_reason = None
        if status == "missing":
            missing_reason = "No matching raw file or processed CSV was found."
        elif status == "partial":
            missing_reason = "Processed file exists, but catalog status or manifest statistics are incomplete."
        elif status == "raw_only":
            missing_reason = "Raw source exists, but no processed CSV was found."
        elif status == "derived_or_folder":
            missing_reason = "Resolved from a category-folder source instead of a single flat table."

        if processed_exists:
            summary["processed"] += 1
        if status == "available":
            summary["available"] += 1
        elif status == "missing":
            summary["missing"] += 1
        elif status == "partial":
            summary["partial"] += 1
        elif status == "raw_only":
            summary["rawOnly"] += 1
        elif status == "derived_or_folder":
            summary["derivedOrFolder"] += 1

        source_workbook = str(manifest.get("source_workbook_name") or "").strip()
        if not source_workbook and raw_path:
            source_workbook = Path(raw_path).name

        entries.append({
            "id": f"{grain}/{table_id}",
            "grain": grain,
            "tableId": table_id,
            "category": grain,
            "type": table_id,
            "status": status,
            "description": catalog_entry.get("description") or cfg.get("description") or "",
            "expectedColumns": catalog_entry.get("expected_columns") or cfg.get("important_fields") or [],
            "processedTableId": catalog_entry.get("processed_table_id") or table_id,
            "processedPath": _safe_relative_path(processed_path) if processed_path and processed_exists else (processed_rel or None),
            "path": raw_path or (_safe_relative_path(processed_path) if processed_path and processed_exists else None),
            "rawdataPath": rawdata_path,
            "rawdataExists": rawdata_exists,
            "rawdataFileCount": rawdata_file_count,
            "rawdataFolderCount": rawdata_folder_count,
            "rawdataHasCsv": rawdata_has_csv,
            "rawdataCsvFileCount": rawdata_csv_file_count,
            "rawdataCsvFolderCount": rawdata_csv_folder_count,
            "v2SourceRule": _v2_source_rule(grain, table_id, resolution_mode),
            "sourceWorkbookName": source_workbook or None,
            "sourceSheet": manifest.get("source_sheet") or cfg.get("source_sheet"),
            "rowCount": manifest.get("row_count"),
            "columnCount": manifest.get("column_count"),
            "lastUpdated": manifest.get("extracted_at") or manifest.get("source_modified_time"),
            "usedByModules": module_usage.get(table_id, []),
            "resolutionMode": resolution_mode,
            "missingReason": missing_reason,
        })

    summary["total"] = len(entries)
    return {
        "entries": entries,
        "rawdataRoot": _safe_relative_path(RAW_DATA_DIR),
        "rawdataTree": rawdata_tree,
        "lastSynced": _utc_now(),
        "summary": summary,
    }


def _v2_source_rule(grain: str, table_id: str, resolution_mode: str | None) -> str:
    if grain == "item" or resolution_mode == "category_folder":
        return "V2 Scope reads item CSV folders under CateMate_rawdata/item/{L1}/{L2}/{L3}/."
    if grain == "category":
        return "V2 Scope reads category workbooks under CateMate_rawdata/category/; category runs usually require rawdata."
    if grain == "shop":
        return "V2 Scope reads shop workbooks under CateMate_rawdata/shop/ when shop-grain modules are selected."
    return f"V2 Scope reads rawdata for {grain}/{table_id}."


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateRunRequest(BaseModel):
    requirementText: str
    planningMode: str = "v2_solve_loop"

class ConfirmCategoriesRequest(BaseModel):
    confirmedCategoryIds: list[str]
    feedback: str | None = None

class ClarificationAnswer(BaseModel):
    questionId: str
    answer: str | None = None
    skipped: bool = False

class SubmitClarificationRequest(BaseModel):
    answers: list[ClarificationAnswer]

class ConfirmVisualSpecRequest(BaseModel):
    sections: list[dict[str, Any]]

class IngestRequest(BaseModel):
    category: str
    type: str
    path: str

class UpdateSettingsRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    baseUrl: str | None = None
    defaultPlanningMode: str | None = None
    temperature: float | None = None
    maxTokens: int | None = None
    enabledModules: list[str] | None = None
    defaultTimeGranularity: str | None = None


# ---------------------------------------------------------------------------
# Routes: Health
# ---------------------------------------------------------------------------

@app.get("/api/healthz")
async def healthz():
    return {"status": "ok", "engine": "catemate-fastapi-bridge"}


# ---------------------------------------------------------------------------
# Routes: Tasks (async job polling)
# ---------------------------------------------------------------------------

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task.model_dump()


# ---------------------------------------------------------------------------
# Routes: Runs
# ---------------------------------------------------------------------------

@app.get("/api/runs")
async def list_runs(status: str | None = None, q: str | None = None):
    manifests = iter_pipeline_manifest_paths(OUTPUTS_DIR)
    results = []
    for path in manifests:
        try:
            m = load_pipeline_manifest(path)
        except Exception:
            continue
        if status and m.status != status:
            continue
        if q:
            haystack = f"{m.case_id} {m.request_text}".lower()
            if q.lower() not in haystack:
                continue
        results.append(_manifest_to_dict(m, path))
    return results


@app.get("/api/runs/stats/summary")
async def run_stats():
    manifests = iter_pipeline_manifest_paths(OUTPUTS_DIR)
    by_status: dict[str, int] = {}
    all_runs = []
    for path in manifests:
        try:
            m = load_pipeline_manifest(path)
        except Exception:
            continue
        by_status[m.status] = by_status.get(m.status, 0) + 1
        all_runs.append(_manifest_to_dict(m, path))

    return {
        "total": len(all_runs),
        "byStatus": [{"status": s, "count": c} for s, c in by_status.items()],
        "recentRuns": all_runs[:5],
    }


@app.post("/api/runs", status_code=201)
async def create_run(body: CreateRunRequest):
    task = _new_task()
    task.status = "running"

    async def _run():
        try:
            from app.pipeline_runtime import run_pipeline_from_request_text_subprocess
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: run_pipeline_from_request_text_subprocess(
                    request_text=body.requirementText,
                    planning_mode=body.planningMode,
                ),
            )
            if result.exit_code == 0 and result.manifest_path:
                m = load_pipeline_manifest(result.manifest_path)
                task.result = _manifest_to_dict(m, result.manifest_path)
                task.status = "completed"
            else:
                task.status = "failed"
                task.error = getattr(result, "error_message", None) or "Pipeline failed"
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
        task.completed_at = _utc_now()

    asyncio.create_task(_run())
    return {"taskId": task.id, "status": task.status}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    path = _find_manifest_by_run_id(run_id)
    if not path:
        raise HTTPException(404, "Run not found")
    m = load_pipeline_manifest(path)
    return _manifest_to_dict(m, path)


# ---------------------------------------------------------------------------
# Routes: Understanding / Blueprint / Gaps
# ---------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/understanding")
async def get_understanding(run_id: str):
    path = _find_manifest_by_run_id(run_id)
    if not path:
        raise HTTPException(404, "Run not found")
    m = load_pipeline_manifest(path)
    data = _load_json_artifact(m, "understanding_spec_path")
    if not data:
        raise HTTPException(404, "Understanding not yet generated")
    return data


@app.get("/api/runs/{run_id}/blueprint")
async def get_blueprint(run_id: str):
    path = _find_manifest_by_run_id(run_id)
    if not path:
        raise HTTPException(404, "Run not found")
    m = load_pipeline_manifest(path)
    data = _load_json_artifact(m, "report_blueprint_path")
    if not data:
        raise HTTPException(404, "Blueprint not yet generated")

    chapters = []
    for section in data.get("sections", []):
        chapters.append({
            "id": section.get("section_id", ""),
            "title": section.get("title", ""),
            "modules": [r.get("module_id", "") for r in section.get("runs", [])],
            "metrics": [r.get("metric_id", "") for r in section.get("runs", [])],
            "scopeKind": section.get("scope_kind", "standard"),
        })

    return {
        "chapters": chapters,
        "verdict": data.get("verdict", ""),
    }


@app.get("/api/runs/{run_id}/gaps")
async def get_gaps(run_id: str):
    path = _find_manifest_by_run_id(run_id)
    if not path:
        raise HTTPException(404, "Run not found")
    m = load_pipeline_manifest(path)
    verdict = _load_json_artifact(m, "solve_verdict_path")
    if not verdict:
        return []

    gaps = []
    for g in verdict.get("gaps", []):
        gaps.append({
            "id": g.get("gap_id", str(uuid.uuid4())[:8]),
            "type": g.get("gap_type", "missing_data"),
            "description": g.get("description", ""),
            "severity": g.get("severity", "medium"),
            "affectedModule": g.get("affected_module", ""),
            "suggestion": g.get("suggestion", ""),
        })
    return gaps


# ---------------------------------------------------------------------------
# Routes: Gates (Category, Clarification, Visual Spec)
# ---------------------------------------------------------------------------

@app.post("/api/runs/{run_id}/gates/category")
async def confirm_categories(run_id: str, body: ConfirmCategoriesRequest):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")

    manifest = load_pipeline_manifest(manifest_path)
    spec_path = resolve_manifest_path(CATEMATE_ROOT, manifest.understanding_spec_path)
    if not spec_path or not spec_path.exists():
        raise HTTPException(400, "Understanding spec not found")

    from catemate.understanding.category_confirmation import confirm_categories as do_confirm, finalize_after_category_confirmation
    from catemate.understanding.clarification import save_understanding_spec, normalize_clarifying_question_ids
    from catemate.understanding.schemas import RequirementUnderstandingSpec
    from catemate.ai.client import CateMateAIClient
    from catemate.ai.settings import AISettings

    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    spec = normalize_clarifying_question_ids(RequirementUnderstandingSpec.model_validate(spec_data))

    if body.feedback:
        from catemate.understanding.category_confirmation import apply_category_feedback
        client = CateMateAIClient(AISettings.from_env())
        spec = apply_category_feedback(spec, body.feedback, ai_client=client)
        save_understanding_spec(spec, spec_path)

    if body.confirmedCategoryIds:
        client = CateMateAIClient(AISettings.from_env())
        spec = do_confirm(spec, body.confirmedCategoryIds)
        spec = finalize_after_category_confirmation(spec, ai_client=client)
        save_understanding_spec(spec, spec_path)

        update_and_save_manifest(
            manifest_path=manifest_path,
            case_id=manifest.case_id,
            timestamp=manifest.timestamp,
            request_text=manifest.request_text,
            provider=manifest.provider,
            model=manifest.model,
            planning_mode=manifest.planning_mode,
            case_config_path=manifest.case_config_path,
            understanding_spec_path=spec_path,
            status="category_confirmed",
        )

    manifest = load_pipeline_manifest(manifest_path)
    return _manifest_to_dict(manifest, manifest_path)


@app.post("/api/runs/{run_id}/gates/clarification")
async def submit_clarification(run_id: str, body: SubmitClarificationRequest):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")

    manifest = load_pipeline_manifest(manifest_path)
    spec_path = resolve_manifest_path(CATEMATE_ROOT, manifest.understanding_spec_path)
    if not spec_path or not spec_path.exists():
        raise HTTPException(400, "Understanding spec not found")

    from catemate.understanding.clarification import (
        apply_clarification_answer,
        save_understanding_spec,
        normalize_clarifying_question_ids,
        is_clarification_complete,
    )
    from catemate.understanding.schemas import RequirementUnderstandingSpec

    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    spec = normalize_clarifying_question_ids(RequirementUnderstandingSpec.model_validate(spec_data))

    for ans in body.answers:
        spec = apply_clarification_answer(
            spec,
            ans.questionId,
            answer_text=ans.answer or "",
            skipped=ans.skipped,
        )
        if not ans.skipped and ans.answer:
            q = next((q for q in spec.clarifying_questions if q.question_id == ans.questionId), None)
            if q and q.rawdata_grain and q.rawdata_table_id:
                try:
                    from catemate.data.rawdata_ingest import ingest_rawdata_from_path
                    ingest_rawdata_from_path(
                        source_path=ans.answer.strip(),
                        grain=q.rawdata_grain,
                        table_id=q.rawdata_table_id,
                    )
                except Exception:
                    pass

    save_understanding_spec(spec, spec_path)

    if is_clarification_complete(spec):
        from app.clarification_editor import mark_clarification_completed
        mark_clarification_completed(manifest, manifest_path)

    manifest = load_pipeline_manifest(manifest_path)
    return _manifest_to_dict(manifest, manifest_path)


@app.post("/api/runs/{run_id}/gates/visual-spec")
async def confirm_visual_spec(run_id: str, body: ConfirmVisualSpecRequest):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")

    manifest = load_pipeline_manifest(manifest_path)
    spec_path = resolve_manifest_path(CATEMATE_ROOT, manifest.visual_report_spec_path)
    if not spec_path or not spec_path.exists():
        raise HTTPException(400, "Visual report spec not found")

    from catemate.html_report.proposal_generator import load_visual_report_spec, save_visual_report_spec

    spec = load_visual_report_spec(spec_path)
    confirmed = spec.model_copy(update={"spec_status": "confirmed"})
    save_visual_report_spec(confirmed, spec_path)

    manifest = load_pipeline_manifest(manifest_path)
    return _manifest_to_dict(manifest, manifest_path)


# ---------------------------------------------------------------------------
# Routes: Solve
# ---------------------------------------------------------------------------

@app.post("/api/runs/{run_id}/solve", status_code=202)
async def trigger_solve(run_id: str):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")

    task = _new_task()
    task.status = "running"

    async def _run():
        try:
            from app.pipeline_runtime import (
                run_pipeline_continue_after_category_confirmation_subprocess,
                run_pipeline_continue_from_manifest_subprocess,
            )

            manifest = load_pipeline_manifest(manifest_path)
            loop = asyncio.get_event_loop()

            if manifest.status in ("category_confirmed", "clarification_completed"):
                if manifest.planning_mode == "v2_solve_loop" and manifest.status == "category_confirmed":
                    result = await loop.run_in_executor(
                        None,
                        lambda: run_pipeline_continue_after_category_confirmation_subprocess(manifest_path),
                    )
                else:
                    result = await loop.run_in_executor(
                        None,
                        lambda: run_pipeline_continue_from_manifest_subprocess(manifest_path),
                    )
            else:
                result = await loop.run_in_executor(
                    None,
                    lambda: run_pipeline_continue_from_manifest_subprocess(manifest_path),
                )

            m = load_pipeline_manifest(manifest_path)
            task.result = _manifest_to_dict(m, manifest_path)
            task.status = "completed" if (result.exit_code == 0) else "failed"
            if result.exit_code != 0:
                task.error = getattr(result, "error_message", None) or "Solve failed"
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
        task.completed_at = _utc_now()

    asyncio.create_task(_run())
    return {"taskId": task.id, "status": task.status}


# ---------------------------------------------------------------------------
# Routes: Brief
# ---------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/brief")
async def get_brief(run_id: str):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")
    m = load_pipeline_manifest(manifest_path)

    md_path = resolve_manifest_path(CATEMATE_ROOT, m.conclusion_brief_path)
    json_path = resolve_manifest_path(CATEMATE_ROOT, m.conclusion_brief_json_path)

    markdown = ""
    if md_path and md_path.exists():
        markdown = md_path.read_text(encoding="utf-8")

    key_findings = []
    if json_path and json_path.exists():
        try:
            brief_data = json.loads(json_path.read_text(encoding="utf-8"))
            key_findings = brief_data.get("key_findings", [])
        except Exception:
            pass

    if not markdown and not key_findings:
        raise HTTPException(404, "Brief not found")

    return {
        "markdown": markdown,
        "keyFindings": key_findings,
        "generatedAt": _utc_now(),
    }


@app.post("/api/runs/{run_id}/brief", status_code=202)
async def generate_brief(run_id: str):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")

    task = _new_task()
    task.status = "running"

    async def _run():
        try:
            from app.pipeline_runtime import run_conclusion_brief_subprocess
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: run_conclusion_brief_subprocess(pipeline_manifest_path=manifest_path),
            )
            if result.exit_code == 0:
                task.status = "completed"
                m = load_pipeline_manifest(manifest_path)
                task.result = _manifest_to_dict(m, manifest_path)
            else:
                task.status = "failed"
                task.error = result.error_message or "Brief generation failed"
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
        task.completed_at = _utc_now()

    asyncio.create_task(_run())
    return {"taskId": task.id, "status": task.status}


# ---------------------------------------------------------------------------
# Routes: Visual Report Spec & HTML / Print Reports
# ---------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/visual-spec")
async def get_visual_spec(run_id: str):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")
    m = load_pipeline_manifest(manifest_path)
    spec_path = resolve_manifest_path(CATEMATE_ROOT, m.visual_report_spec_path)
    if not spec_path or not spec_path.exists():
        raise HTTPException(404, "Visual spec not found")

    from catemate.html_report.proposal_generator import load_visual_report_spec
    spec = load_visual_report_spec(spec_path)
    return spec.model_dump(mode="json")


@app.post("/api/runs/{run_id}/visual-spec", status_code=202)
async def generate_visual_spec(run_id: str):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")

    task = _new_task()
    task.status = "running"

    async def _run():
        try:
            from app.pipeline_runtime import run_visual_report_subprocess
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: run_visual_report_subprocess(pipeline_manifest_path=manifest_path, mode="propose"),
            )
            if result.exit_code == 0:
                task.status = "completed"
                m = load_pipeline_manifest(manifest_path)
                task.result = _manifest_to_dict(m, manifest_path)
            else:
                task.status = "failed"
                task.error = result.error_message or "Visual spec generation failed"
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
        task.completed_at = _utc_now()

    asyncio.create_task(_run())
    return {"taskId": task.id, "status": task.status}


@app.post("/api/runs/{run_id}/html-report", status_code=202)
async def generate_html_report(run_id: str):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")

    task = _new_task()
    task.status = "running"

    async def _run():
        try:
            from app.pipeline_runtime import run_visual_report_subprocess
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: run_visual_report_subprocess(pipeline_manifest_path=manifest_path, mode="render"),
            )
            if result.exit_code == 0:
                task.status = "completed"
                m = load_pipeline_manifest(manifest_path)
                task.result = _manifest_to_dict(m, manifest_path)
            else:
                task.status = "failed"
                task.error = result.error_message or "HTML report render failed"
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
        task.completed_at = _utc_now()

    asyncio.create_task(_run())
    return {"taskId": task.id, "status": task.status}


@app.post("/api/runs/{run_id}/print-report", status_code=202)
async def generate_print_report(run_id: str):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")

    task = _new_task()
    task.status = "running"

    async def _run():
        try:
            from app.pipeline_runtime import run_print_report_subprocess
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: run_print_report_subprocess(pipeline_manifest_path=manifest_path),
            )
            if result.exit_code == 0:
                task.status = "completed"
                m = load_pipeline_manifest(manifest_path)
                task.result = _manifest_to_dict(m, manifest_path)
            else:
                task.status = "failed"
                task.error = result.error_message or "Print report failed"
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
        task.completed_at = _utc_now()

    asyncio.create_task(_run())
    return {"taskId": task.id, "status": task.status}


@app.get("/api/runs/{run_id}/deliverables")
async def get_deliverables(run_id: str):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")
    m = load_pipeline_manifest(manifest_path)
    return _build_deliverables(m, manifest_path)


# ---------------------------------------------------------------------------
# Routes: Static file serving for outputs
# ---------------------------------------------------------------------------

@app.get("/api/files/{file_path:path}")
async def serve_file(file_path: str):
    full = CATEMATE_ROOT / file_path
    full = full.resolve()
    if not str(full).startswith(str(CATEMATE_ROOT)):
        raise HTTPException(403, "Access denied")
    if not full.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(full)


# ---------------------------------------------------------------------------
# Routes: Datasources
# ---------------------------------------------------------------------------

@app.get("/api/datasources")
async def get_datasources():
    return _build_datasource_catalog_response()


@app.post("/api/datasources/ingest", status_code=202)
async def ingest_datasource(body: IngestRequest):
    try:
        from catemate.data.rawdata_ingest import ingest_rawdata_from_path
        ingest_rawdata_from_path(
            source_path=body.path,
            grain=body.category,
            table_id=body.type,
        )
        return {"status": "ok", "message": f"Ingested {body.path}"}
    except Exception as exc:
        raise HTTPException(400, str(exc))


# ---------------------------------------------------------------------------
# Routes: Settings
# ---------------------------------------------------------------------------

@app.get("/api/settings")
async def get_settings():
    from dotenv import dotenv_values
    env = dotenv_values(CATEMATE_ROOT / ".env")

    enabled_modules = []
    policy_path = CONFIG_DIR / "output_grain_policy.yaml"
    if policy_path.exists():
        import yaml
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        if isinstance(policy, dict):
            enabled_modules = policy.get("enabled_v2_modules", [])

    return {
        "provider": env.get("CATEMATE_AI_PROVIDER", "deepseek"),
        "model": env.get("DEEPSEEK_MODEL", env.get("CATEMATE_OPENAI_MODEL", "")),
        "baseUrl": env.get("DEEPSEEK_BASE_URL", env.get("CATEMATE_OPENAI_BASE_URL", "")),
        "defaultPlanningMode": "v2_solve_loop",
        "temperature": float(env.get("CATEMATE_AI_TEMPERATURE", "0")) if env.get("CATEMATE_AI_TEMPERATURE") else None,
        "maxTokens": int(env.get("CATEMATE_AI_MAX_TOKENS", "0")) if env.get("CATEMATE_AI_MAX_TOKENS") else None,
        "enabledModules": enabled_modules,
        "defaultTimeGranularity": "month",
    }


@app.put("/api/settings")
async def update_settings(body: UpdateSettingsRequest):
    env_path = CATEMATE_ROOT / ".env"
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    def _set_env(key: str, value: str | None):
        nonlocal lines
        if value is None:
            return
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}")

    if body.provider:
        _set_env("CATEMATE_AI_PROVIDER", body.provider)
    if body.model:
        _set_env("DEEPSEEK_MODEL", body.model)
    if body.baseUrl:
        _set_env("DEEPSEEK_BASE_URL", body.baseUrl)
    if body.temperature is not None:
        _set_env("CATEMATE_AI_TEMPERATURE", str(body.temperature))
    if body.maxTokens is not None:
        _set_env("CATEMATE_AI_MAX_TOKENS", str(body.maxTokens))

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return await get_settings()


# ---------------------------------------------------------------------------
# Routes: Modules
# ---------------------------------------------------------------------------

@app.get("/api/modules")
async def list_modules():
    from catemate.planning.context_loader import load_v2_data_module_contracts

    modules = []
    try:
        contracts = load_v2_data_module_contracts(active_only=False)
    except Exception:
        contracts = []

    for c in contracts:
        module_id = c.get("module_id", "")
        modules.append({
            "id": module_id,
            "name": c.get("name", module_id),
            "status": c.get("status", "draft"),
            "description": c.get("description", ""),
            "metrics": [m.get("metric_id", "") for m in c.get("metrics", [])],
            "applicableScenes": c.get("applicable_scenes", []),
            "outputTables": [t.get("table_id", "") for t in c.get("output_tables", [])],
        })

    return modules


# ---------------------------------------------------------------------------
# Routes: V1 Compatibility (Module Selection, Confirmation Gate, PPT-ready)
# ---------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/module-selection")
async def get_module_selection(run_id: str):
    path = _find_manifest_by_run_id(run_id)
    if not path:
        raise HTTPException(404, "Run not found")
    m = load_pipeline_manifest(path)
    data = _load_json_artifact(m, "module_selection_plan_path")
    if not data:
        raise HTTPException(404, "Module selection not available")
    return data


@app.get("/api/runs/{run_id}/confirmation")
async def get_confirmation(run_id: str):
    path = _find_manifest_by_run_id(run_id)
    if not path:
        raise HTTPException(404, "Run not found")
    m = load_pipeline_manifest(path)
    wb_path = resolve_manifest_path(CATEMATE_ROOT, m.requirement_workbook_path)
    if not wb_path or not wb_path.exists():
        raise HTTPException(404, "Requirement workbook not found")

    from catemate.core.confirmation_reader import read_confirmation_records
    from catemate.core.confirmation_gate import evaluate_confirmation_gate, ConfirmationItem

    records = read_confirmation_records(wb_path)
    items = [
        ConfirmationItem(
            name=str(r.get("确认项名称", "")),
            suggested_value=str(r.get("建议值", "")),
            status=str(r.get("状态", "待确认")),
            reason=str(r.get("原因", "")),
        )
        for r in records
    ]
    gate = evaluate_confirmation_gate(items)

    return {
        "items": [
            {"row": r.get("row"), "name": r.get("确认项名称"), "suggestedValue": r.get("建议值"),
             "status": r.get("状态"), "reason": r.get("原因"), "blocksPptReady": r.get("是否阻止PPT-ready生成")}
            for r in records
        ],
        "canGenerate": gate.can_generate,
        "message": gate.message,
        "blockingCount": len(gate.blocking_items),
    }


class ConfirmationUpdateRequest(BaseModel):
    statuses: dict[str, str]  # row number -> new status

@app.post("/api/runs/{run_id}/confirmation")
async def update_confirmation(run_id: str, body: ConfirmationUpdateRequest):
    path = _find_manifest_by_run_id(run_id)
    if not path:
        raise HTTPException(404, "Run not found")
    m = load_pipeline_manifest(path)
    wb_path = resolve_manifest_path(CATEMATE_ROOT, m.requirement_workbook_path)
    if not wb_path or not wb_path.exists():
        raise HTTPException(400, "Requirement workbook not found")

    from catemate.core.confirmation_writer import save_confirmation_updates
    int_statuses = {int(k): v for k, v in body.statuses.items()}
    saved = save_confirmation_updates(wb_path, int_statuses, wb_path)
    return {"saved": str(saved), "status": "ok"}


@app.post("/api/runs/{run_id}/ppt-ready", status_code=202)
async def generate_ppt_ready(run_id: str):
    manifest_path = _find_manifest_by_run_id(run_id)
    if not manifest_path:
        raise HTTPException(404, "Run not found")

    task = _new_task()
    task.status = "running"

    async def _run():
        try:
            m = load_pipeline_manifest(manifest_path)
            wb_path = resolve_manifest_path(CATEMATE_ROOT, m.requirement_workbook_path)
            spec_path = resolve_manifest_path(CATEMATE_ROOT, m.planning_spec_path)
            if not wb_path or not spec_path:
                task.status = "failed"
                task.error = "Workbook or planning spec not found"
                return

            from app.pipeline_runtime import run_ppt_ready_subprocess
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: run_ppt_ready_subprocess(
                    requirement_workbook=wb_path,
                    planning_spec_path=spec_path,
                    pipeline_manifest_path=manifest_path,
                ),
            )
            if result.exit_code == 0:
                task.status = "completed"
                updated = load_pipeline_manifest(manifest_path)
                task.result = _manifest_to_dict(updated, manifest_path)
            else:
                task.status = "failed"
                task.error = result.error_message or "PPT-ready generation failed"
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
        task.completed_at = _utc_now()

    asyncio.create_task(_run())
    return {"taskId": task.id, "status": task.status}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "catemate_api:app",
        host="0.0.0.0",
        port=8100,
        reload=True,
        reload_dirs=[str(PROJECT_ROOT / "api"), str(PROJECT_ROOT / "app"), str(PROJECT_ROOT / "catemate")],
    )
