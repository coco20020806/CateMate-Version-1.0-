"""Load and query English category tree from CateMate_rawdata/category_tree_en.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from catemate.core.paths import CATEGORY_TREE_EN_PATH


@dataclass(frozen=True)
class CategoryTreePath:
    l1: str
    l2: str = ""
    l3: str = ""
    path: str = ""
    depth: int = 1

    def __post_init__(self) -> None:
        if not self.path:
            parts = [part for part in [self.l1, self.l2, self.l3] if part]
            object.__setattr__(self, "path", " > ".join(parts))
        if not self.depth:
            object.__setattr__(self, "depth", sum(1 for part in [self.l1, self.l2, self.l3] if part))


def load_category_tree_en(path: Path | None = None) -> list[dict[str, Any]]:
    tree_path = path or CATEGORY_TREE_EN_PATH
    if not tree_path.exists():
        raise FileNotFoundError(f"Category tree JSON not found: {tree_path}")
    payload = json.loads(tree_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Category tree root must be a list: {tree_path}")
    return payload


def flatten_category_tree(tree: list[dict[str, Any]] | None = None) -> list[CategoryTreePath]:
    """Flatten nested L1/L2/L3 tree nodes into unique paths."""
    tree = tree if tree is not None else load_category_tree_en()
    paths: list[CategoryTreePath] = []
    seen: set[tuple[str, str, str]] = set()

    def add_path(l1: str, l2: str = "", l3: str = "") -> None:
        l1 = l1.strip()
        l2 = l2.strip()
        l3 = l3.strip()
        if not l1:
            return
        key = (l1, l2, l3)
        if key in seen:
            return
        seen.add(key)
        depth = sum(1 for part in [l1, l2, l3] if part)
        paths.append(CategoryTreePath(l1=l1, l2=l2, l3=l3, depth=depth))

    for l1_node in tree:
        if not isinstance(l1_node, dict):
            continue
        l1_name = str(l1_node.get("name") or "").strip()
        if not l1_name:
            continue
        add_path(l1_name)
        for l2_node in l1_node.get("children") or []:
            if not isinstance(l2_node, dict):
                continue
            l2_name = str(l2_node.get("name") or "").strip()
            if not l2_name:
                continue
            add_path(l1_name, l2_name)
            for l3_node in l2_node.get("children") or []:
                if not isinstance(l3_node, dict):
                    continue
                l3_name = str(l3_node.get("name") or "").strip()
                if l3_name:
                    add_path(l1_name, l2_name, l3_name)

    return paths


@lru_cache(maxsize=1)
def cached_category_paths() -> tuple[CategoryTreePath, ...]:
    return tuple(flatten_category_tree())


def list_category_tree_candidates(*, include_l2_only: bool = True) -> list[dict[str, str]]:
    """Candidates for understanding prompts (L3 rows plus optional L2-only rows)."""
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in cached_category_paths():
        if item.l3:
            key = item.path
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "l1": item.l1,
                    "l2": item.l2,
                    "l3": item.l3,
                    "category_path": item.path,
                }
            )
        elif include_l2_only and item.l2:
            key = item.path
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "l1": item.l1,
                    "l2": item.l2,
                    "l3": "",
                    "category_path": item.path,
                }
            )
    return candidates


def find_path_in_tree(l1: str = "", l2: str = "", l3: str = "") -> CategoryTreePath | None:
    l1 = l1.strip()
    l2 = l2.strip()
    l3 = l3.strip()
    for item in cached_category_paths():
        if item.l1 == l1 and item.l2 == l2 and item.l3 == l3:
            return item
    return None
