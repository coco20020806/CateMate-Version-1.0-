"""Inventory outputs/ for archive + rollbackable cleanup planning. Does not delete."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "outputs"
REPORT = ROOT / "_cleanup_inventory.json"
REPORT_MD = ROOT / "_cleanup_inventory.md"


def main() -> int:
    files = [p for p in ROOT.iterdir() if p.is_file() and not p.name.startswith("_cleanup_")]
    referenced: set[Path] = set()
    runs: list[dict] = []

    for mpath in sorted(ROOT.glob("pipeline_manifest_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = json.loads(mpath.read_text(encoding="utf-8"))
        case_id = data.get("case_id") or "unknown"
        ts = data.get("timestamp") or mpath.stem
        run_id = f"{case_id}_{ts}"
        group_files: list[str] = [mpath.name]
        missing: list[str] = []
        referenced.add(mpath.resolve())

        planning_case_id = ""
        for key in [
            "case_config_path",
            "understanding_spec_path",
            "module_selection_plan_path",
            "planning_spec_path",
            "requirement_workbook_path",
            "ppt_ready_workbook_path",
            "html_preview_path",
        ]:
            raw = data.get(key)
            if not raw:
                continue
            path = Path(raw)
            if path.exists():
                referenced.add(path.resolve())
                if path.name not in group_files:
                    group_files.append(path.name)
            else:
                missing.append(path.name)
            if key == "planning_spec_path" and path.exists():
                try:
                    planning_case_id = (
                        json.loads(path.read_text(encoding="utf-8")).get("case_id") or ""
                    )
                except Exception:
                    planning_case_id = ""

        # Attach same-run siblings by case_id+timestamp, confirmed workbooks, and planning case ppt files.
        for path in ROOT.iterdir():
            if not path.is_file():
                continue
            name = path.name
            linked = False
            if case_id != "unknown" and case_id in name and ts in name:
                linked = True
            if "_confirmed_" in name and case_id in name and ts in name:
                linked = True
            if planning_case_id and name.startswith("ppt_ready_workbook_") and planning_case_id in name:
                linked = True
            if linked:
                referenced.add(path.resolve())
                if name not in group_files:
                    group_files.append(name)

        bytes_total = sum((ROOT / n).stat().st_size for n in group_files if (ROOT / n).exists())
        action = "keep_active"
        if data.get("status") == "failed" and len(group_files) <= 2:
            action = "archive_failed_empty"
        elif data.get("status") == "failed":
            action = "archive_failed_partial"
        elif data.get("status") in {"workbook_generated", "completed"}:
            action = "keep_or_archive_old_run"
        elif data.get("status") == "ppt_ready_generated":
            action = "keep_active"

        runs.append(
            {
                "run_id": run_id,
                "manifest": mpath.name,
                "case_id": case_id,
                "timestamp": ts,
                "status": data.get("status"),
                "error_message": (data.get("error_message") or "")[:120],
                "planning_case_id": planning_case_id,
                "file_count": len(group_files),
                "bytes": bytes_total,
                "files": sorted(group_files),
                "missing": missing,
                "proposed_action": action,
                "proposed_dir": f"outputs/runs/{run_id}",
            }
        )

    orphans = sorted(
        p.name for p in files if p.resolve() not in referenced and not p.name.startswith("_cleanup_")
    )
    orphan_rows = []
    for name in orphans:
        path = ROOT / name
        size = path.stat().st_size
        if name.startswith("ppt_ready_workbook_"):
            action = "archive_superseded_ppt"
            reason = "未挂在当前 manifest 最新路径上的 PPT/HTML（多为重试产物）"
        elif name.startswith("pipeline_manifest_") and "generated_case_" in name:
            action = "archive_failed_empty"
            reason = "空失败 manifest"
        elif any(
            name.startswith(prefix)
            for prefix in (
                "category_analysis_",
                "planning_spec_",
                "generated_case_config_",
                "module_selection_",
                "requirement_understanding_",
            )
        ):
            action = "archive_orphan_artifact"
            reason = "无对应 manifest 引用，或旧链路产物"
        else:
            action = "manual_review"
            reason = "需人工确认"
        orphan_rows.append(
            {
                "file": name,
                "bytes": size,
                "proposed_action": action,
                "reason": reason,
                "proposed_dir": "outputs/_quarantine/orphans",
            }
        )

    # Within each ppt-ready run, mark older ppt files as superseded keep-one-latest.
    for run in runs:
        if run["status"] != "ppt_ready_generated":
            continue
        ppt_files = [
            n
            for n in run["files"]
            if n.startswith("ppt_ready_workbook_") and n.endswith(".xlsx")
        ]
        html_files = [
            n
            for n in run["files"]
            if n.startswith("ppt_ready_workbook_") and n.endswith("_preview.html")
        ]
        ppt_files_sorted = sorted(ppt_files)
        html_files_sorted = sorted(html_files)
        run["keep_latest_ppt"] = ppt_files_sorted[-1] if ppt_files_sorted else None
        run["archive_older_ppt"] = ppt_files_sorted[:-1]
        run["keep_latest_html"] = html_files_sorted[-1] if html_files_sorted else None
        run["archive_older_html"] = html_files_sorted[:-1]

    summary = {
        "total_files": len(files),
        "total_bytes": sum(p.stat().st_size for p in files),
        "run_count": len(runs),
        "orphan_count": len(orphans),
        "orphan_bytes": sum(r["bytes"] for r in orphan_rows),
        "by_action": defaultdict(int),
    }
    for run in runs:
        summary["by_action"][run["proposed_action"]] += 1
    for row in orphan_rows:
        summary["by_action"][row["proposed_action"]] += 1
    summary["by_action"] = dict(summary["by_action"])

    payload = {
        "summary": summary,
        "policy": {
            "phase1": "只生成清单与目录规划，不移动不删除",
            "phase2": "把文件 move 到 outputs/runs/<run_id>/ 与 outputs/_quarantine/，并写 rollback map",
            "phase3": "确认无误后，再把 _quarantine 中明确无用项移到 outputs/_trash/ 或删除",
            "rollback": "用 rollback map 把文件移回原路径，并恢复 manifest 内绝对路径",
            "never_auto_delete": True,
        },
        "runs": runs,
        "orphans": orphan_rows,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# outputs 清理清单（只读，未删除）",
        "",
        f"- 总文件数：{summary['total_files']}",
        f"- 总大小：{summary['total_bytes'] / 1024 / 1024:.1f} MB",
        f"- run（manifest）数：{summary['run_count']}",
        f"- 孤儿文件数：{summary['orphan_count']}（约 {summary['orphan_bytes'] / 1024 / 1024:.1f} MB）",
        "",
        "## 建议动作统计",
        "",
    ]
    for action, count in sorted(summary["by_action"].items()):
        lines.append(f"- `{action}`: {count}")

    lines.extend(["", "## Run 清单", ""])
    for run in runs:
        lines.append(
            f"### `{run['run_id']}` — `{run['status']}` → **{run['proposed_action']}**"
        )
        lines.append(f"- manifest: `{run['manifest']}`")
        lines.append(f"- 文件数/大小: {run['file_count']} / {run['bytes'] / 1024 / 1024:.2f} MB")
        lines.append(f"- 目标目录: `{run['proposed_dir']}`")
        if run.get("error_message"):
            lines.append(f"- error: {run['error_message']}")
        if run.get("keep_latest_ppt"):
            lines.append(f"- 保留最新 PPT: `{run['keep_latest_ppt']}`")
        if run.get("archive_older_ppt"):
            lines.append(
                "- 可归档旧 PPT: "
                + ", ".join(f"`{n}`" for n in run["archive_older_ppt"])
            )
        if run.get("keep_latest_html"):
            lines.append(f"- 保留最新 HTML: `{run['keep_latest_html']}`")
        if run.get("archive_older_html"):
            lines.append(
                "- 可归档旧 HTML: "
                + ", ".join(f"`{n}`" for n in run["archive_older_html"])
            )
        lines.append("- 文件:")
        for name in run["files"]:
            lines.append(f"  - `{name}`")
        if run["missing"]:
            lines.append("- 缺失引用:")
            for name in run["missing"]:
                lines.append(f"  - `{name}`")
        lines.append("")

    lines.extend(["## 孤儿文件", ""])
    for row in orphan_rows:
        lines.append(
            f"- `{row['file']}` ({row['bytes'] / 1024:.1f} KB) → **{row['proposed_action']}** — {row['reason']}"
        )

    lines.extend(
        [
            "",
            "## 执行阶段（需你确认后再做）",
            "",
            "1. **Phase 1（已完成）**：生成本清单，不改动文件。",
            "2. **Phase 2**：`move` 到 `outputs/runs/<run_id>/` 与 `outputs/_quarantine/`，写 `rollback_map.json`。",
            "3. **Phase 3**：确认 Streamlit/CLI 仍可用后，再处理 `_quarantine`（仍建议先移到 `_trash`，保留 7–14 天）。",
            "",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT}")
    print(f"Wrote {REPORT_MD}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
