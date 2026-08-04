"""Fail fast when a public CateMate checkout contains unsafe tracked content."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_TRACKED_FILE_BYTES = 2 * 1024 * 1024
TEXT_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".yml", ".json", ".csv", ".ps1", ".toml"}
PATH_FORBIDDEN = {
    "Private environment file": re.compile(r"(^|/)\.env($|\.)"),
    "Private data directory": re.compile(r"^(CateMate_rawdata|CateMate_processeddata|outputs)/", re.IGNORECASE),
}
CONTENT_FORBIDDEN = {
    "Shopee brand reference": re.compile(r"\bshopee\b", re.IGNORECASE),
    "Likely API secret": re.compile(r"(?:sk-[A-Za-z0-9]{16,}|api[_-]?key\s*[=:]\s*['\"][^'\"]{12,})", re.IGNORECASE),
}
ALLOWLIST = {".env.example", "CateMate_rawdata/.gitkeep", "CateMate_rawdata/README.md", "CateMate_processeddata/.gitkeep", "CateMate_processeddata/README.md", "outputs/.gitkeep", "outputs/README.md"}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return [line.replace("\\", "/") for line in result.stdout.splitlines()]


def main() -> int:
    findings: list[str] = []
    for relative in tracked_files():
        path = ROOT / relative
        if relative not in ALLOWLIST:
            for label, pattern in PATH_FORBIDDEN.items():
                if pattern.search(relative):
                    findings.append(f"{relative}: {label}")
        if path.is_file() and path.stat().st_size > MAX_TRACKED_FILE_BYTES:
            findings.append(f"{relative}: tracked file exceeds 2 MiB")
        if path.suffix.lower() in TEXT_SUFFIXES and path.is_file():
            content = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in CONTENT_FORBIDDEN.items():
                if relative == "scripts/check_public_repo.py" and label == "Shopee brand reference":
                    continue
                if pattern.search(content):
                    findings.append(f"{relative}: {label}")
    if findings:
        print("Public repository check failed:")
        print("\n".join(f"- {item}" for item in findings))
        return 1
    print("Public repository check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
