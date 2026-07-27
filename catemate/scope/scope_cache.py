"""In-memory and on-disk cache for precomputed ScopedFrames."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from catemate.scope.schemas import ScopedFrame, ScopeSpec

MANIFEST_FILENAME = "subset_scope_manifest.json"


def cache_key(spec: ScopeSpec) -> str:
    concept_id = ""
    if spec.related_concept_pack is not None:
        concept_id = spec.related_concept_pack.concept_id
    sites = ",".join(sorted(s.strip().upper() for s in spec.target_sites if s.strip()))
    return "|".join(
        [
            spec.grain,
            spec.table_id,
            spec.category_l1,
            spec.category_l2,
            spec.category_l3,
            concept_id,
            str(spec.related_min_score),
            sites,
        ]
    )


@dataclass
class ScopeCache:
    """Cache ScopedFrames keyed by scope identity (excluding scope_label)."""

    frames: dict[str, ScopedFrame] = field(default_factory=dict)
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)
    disk_dir: Path | None = None

    def get(self, spec: ScopeSpec) -> ScopedFrame | None:
        key = cache_key(spec)
        cached = self.frames.get(key)
        if cached is None:
            return None
        return ScopedFrame(
            data=cached.data.copy(),
            scope_label=spec.scope_label or cached.scope_label,
            scope_spec=dict(cached.scope_spec),
            source_id=cached.source_id,
        )

    def put(self, spec: ScopeSpec, frame: ScopedFrame, *, input_rows: int | None = None) -> None:
        key = cache_key(spec)
        self.frames[key] = ScopedFrame(
            data=frame.data.copy(),
            scope_label=frame.scope_label,
            scope_spec=dict(frame.scope_spec),
            source_id=frame.source_id,
        )
        output_rows = len(frame.data)
        entry = {
            "cache_key": key,
            "grain": spec.grain,
            "table_id": spec.table_id,
            "category_l1": spec.category_l1,
            "category_l2": spec.category_l2,
            "category_l3": spec.category_l3,
            "concept_id": spec.related_concept_pack.concept_id if spec.related_concept_pack else "",
            "min_score": spec.related_min_score,
            "target_sites": list(spec.target_sites),
            "input_rows": input_rows if input_rows is not None else output_rows,
            "output_rows": output_rows,
            "filter_ratio": round(output_rows / input_rows, 4) if input_rows else 1.0,
            "parquet_file": _parquet_filename(key),
            "source_id": frame.source_id,
        }
        entry["csv_file"] = csv_filename_from_entry(entry)
        self.entries[key] = entry

    def save_to_dir(self, run_dir: Path) -> Path:
        cache_dir = Path(run_dir) / "subset_scope"
        cache_dir.mkdir(parents=True, exist_ok=True)
        for key, frame in self.frames.items():
            entry = self.entries.get(key) or {}
            csv_name = csv_filename_from_entry(entry) if entry else f"{key}.csv"
            if key in self.entries:
                self.entries[key]["csv_file"] = csv_name
            csv_path = cache_dir / csv_name
            frame.data.to_csv(csv_path, index=False, encoding="utf-8-sig")
            parquet_path = cache_dir / _parquet_filename(key)
            frame.data.to_parquet(parquet_path, index=False)
        manifest = {
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "entries": list(self.entries.values()),
        }
        manifest_path = cache_dir / MANIFEST_FILENAME
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.disk_dir = cache_dir
        return cache_dir

    @classmethod
    def load_from_dir(cls, run_dir: Path) -> ScopeCache | None:
        cache_dir = Path(run_dir) / "subset_scope"
        manifest_path = cache_dir / MANIFEST_FILENAME
        if not manifest_path.exists():
            return None

        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = payload.get("entries") or []
        cache = cls(disk_dir=cache_dir)
        for entry in entries:
            key = str(entry.get("cache_key") or "")
            parquet_name = str(entry.get("parquet_file") or _parquet_filename(key))
            parquet_path = cache_dir / parquet_name
            if not key or not parquet_path.exists():
                continue
            df = pd.read_parquet(parquet_path)
            cache.frames[key] = ScopedFrame(
                data=df,
                scope_label=_scope_label_from_entry(entry),
                scope_spec={
                    "grain": entry.get("grain"),
                    "table_id": entry.get("table_id"),
                    "target_sites": entry.get("target_sites") or [],
                    "category_l1": entry.get("category_l1"),
                    "category_l2": entry.get("category_l2"),
                    "category_l3": entry.get("category_l3"),
                },
                source_id=str(entry.get("source_id") or ""),
            )
            cache.entries[key] = dict(entry)
        return cache if cache.frames else None

    def summary(self) -> dict[str, Any]:
        if not self.entries:
            return {"hit": False, "entries": 0}
        total_output = sum(int(item.get("output_rows") or 0) for item in self.entries.values())
        return {
            "hit": True,
            "entries": len(self.entries),
            "output_rows": total_output,
            "disk_dir": str(self.disk_dir) if self.disk_dir else "",
        }


def _parquet_filename(key: str) -> str:
    safe = key.replace("|", "__").replace("/", "_")[:180]
    return f"{safe}.parquet"


def csv_filename_from_entry(entry: dict[str, Any]) -> str:
    l1 = _safe_path_segment(str(entry.get("category_l1") or ""))
    l2 = _safe_path_segment(str(entry.get("category_l2") or ""))
    l3 = _safe_path_segment(str(entry.get("category_l3") or ""))
    sites = entry.get("target_sites") or []
    sites_part = "_".join(sorted(str(s).strip().upper() for s in sites if str(s).strip())) or "ALL"
    return f"sub_l3_items__{l1}__{l2}__{l3}__{sites_part}.csv"


def _safe_path_segment(value: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unknown"


def _scope_label_from_entry(entry: dict[str, Any]) -> str:
    parts = []
    sites = entry.get("target_sites") or []
    if sites:
        parts.append("/".join(sites))
    for level in ("category_l1", "category_l2", "category_l3"):
        value = str(entry.get(level) or "").strip()
        if value:
            parts.append(value)
    concept_id = str(entry.get("concept_id") or "").strip()
    if concept_id:
        parts.append(concept_id)
    return " / ".join(parts) or str(entry.get("table_id") or "subset")
