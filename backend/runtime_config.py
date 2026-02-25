"""
Runtime configuration storage.
Stores provider selections in process-local memory.
"""
from __future__ import annotations

from typing import Any, Dict


_runtime_config: Dict[str, Any] = {}


def load_runtime_config() -> Dict[str, Any]:
    return dict(_runtime_config)


def save_runtime_config(config: Dict[str, Any]) -> None:
    _runtime_config.clear()
    _runtime_config.update(dict(config or {}))


def update_runtime_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    config = load_runtime_config()
    config.update(dict(updates or {}))
    save_runtime_config(config)
    return config


def get_runtime_value(key: str, default: Any = None) -> Any:
    config = load_runtime_config()
    return config.get(key, default)
