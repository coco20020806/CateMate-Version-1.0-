"""V2 data module availability for solve loop orchestration."""

from __future__ import annotations

from functools import lru_cache

from catemate.planning.context_loader import load_v2_data_module_contracts


@lru_cache(maxsize=1)
def active_v2_module_ids() -> tuple[str, ...]:
    """Return module_id values with status=active in data_modules/*/contract.yaml."""
    ids = [
        str(contract.get("module_id") or "").strip()
        for contract in load_v2_data_module_contracts(active_only=True)
        if str(contract.get("module_id") or "").strip()
    ]
    return tuple(ids)


def is_active_v2_module(module_id: str) -> bool:
    module_id = str(module_id or "").strip()
    if not module_id:
        return False
    return module_id in active_v2_module_ids()


def clear_active_v2_module_cache() -> None:
    """Clear cached active module ids (for tests)."""
    active_v2_module_ids.cache_clear()
