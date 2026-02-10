"""
Runtime configuration storage.
Stores provider selections in a JSON file without requiring an app restart.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import time


_CONFIG_PATH = Path(__file__).resolve().parents[1] / "app_config.json"

_cache: Dict[str, Any] = {}
_cache_ts: float = 0.0
_CACHE_TTL: float = 2.0  # seconds


def load_runtime_config() -> Dict[str, Any]:
    global _cache, _cache_ts
    now = time.monotonic()
    if _cache and (now - _cache_ts) < _CACHE_TTL:
        return _cache
    if not _CONFIG_PATH.exists():
        _cache, _cache_ts = {}, now
        return _cache
    try:
        with _CONFIG_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            _cache = data if isinstance(data, dict) else {}
    except Exception:
        _cache = {}
    _cache_ts = now
    return _cache


def save_runtime_config(config: Dict[str, Any]) -> None:
    global _cache, _cache_ts
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
    _cache = config.copy()
    _cache_ts = time.monotonic()


def update_runtime_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    config = load_runtime_config()
    config.update(updates)
    save_runtime_config(config)
    return config


def get_runtime_value(key: str, default: Any = None) -> Any:
    config = load_runtime_config()
    return config.get(key, default)
