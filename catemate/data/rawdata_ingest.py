"""Ingest user-supplied rawdata file paths into grain directories."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from catemate.core.paths import PROJECT_ROOT, RAWDATA_GRAIN_DIRS
from catemate.data.rawdata_catalog import update_catalog_status


def ingest_rawdata_from_path(
    *,
    source_path: str | Path,
    grain: str,
    table_id: str,
    catalog_path: Path | None = None,
    run_preprocess: bool = True,
) -> dict:
    src = Path(source_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"源文件不存在: {src}")
    if src.suffix.lower() not in {".xlsx", ".xls"}:
        raise ValueError(f"仅支持 Excel 文件: {src}")

    if grain not in RAWDATA_GRAIN_DIRS:
        raise ValueError(f"未知 grain={grain}; 期望 category|shop|item")

    dest_dir = RAWDATA_GRAIN_DIRS[grain]  # type: ignore[index]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)

    update_catalog_status(table_id, "available", catalog_path=catalog_path, file_path=str(dest))

    preprocess_note = ""
    if run_preprocess:
        script = PROJECT_ROOT / "scripts" / "preprocess_raw_data_sources.py"
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        preprocess_note = proc.stdout[-500:] if proc.stdout else ""
        if proc.returncode != 0:
            raise RuntimeError(f"预处理失败: {proc.stderr or proc.stdout}")

    return {
        "grain": grain,
        "table_id": table_id,
        "source_path": str(src),
        "dest_path": str(dest),
        "catalog_status": "available",
        "preprocess_note": preprocess_note,
    }
