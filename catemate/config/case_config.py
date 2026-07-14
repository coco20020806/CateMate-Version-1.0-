"""Case config loader for category analysis requirement generation."""

from __future__ import annotations

from pathlib import Path

from catemate.schemas.category_requirement import CategoryAnalysisCaseConfig


def load_case_config(path: Path) -> CategoryAnalysisCaseConfig:
    """Load a category analysis case config from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Case config not found: {path}")

    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on runtime env.
        raise RuntimeError(
            "PyYAML is required to read case config YAML files. "
            "Please install it with `pip install PyYAML`."
        ) from exc

    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}

    if not isinstance(payload, dict):
        raise ValueError(f"Invalid case config format in {path}: top-level must be a mapping")

    return CategoryAnalysisCaseConfig.model_validate(payload)

