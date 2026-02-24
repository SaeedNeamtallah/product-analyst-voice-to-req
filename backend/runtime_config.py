"""
Runtime configuration storage.
Stores provider selections in Redis with process-local TTL cache.
"""
from __future__ import annotations

from typing import Any, Dict
import json
import time

from redis import Redis

from backend.config import settings
from backend.services.redis_keyspace import RedisKeyspace


_RUNTIME_CONFIG_KEY = RedisKeyspace.lock("runtime", "app_config")

_cache: Dict[str, Any] = {}
_cache_ts: float = 0.0
_CACHE_TTL: float = 10.0  # seconds
_redis_client: Redis | None = None


def _get_redis_client() -> Redis | None:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if not bool(settings.redis_enabled and str(settings.redis_url or "").strip()):
        return None

    try:
        _redis_client = Redis.from_url(
            str(settings.redis_url),
            decode_responses=True,
            socket_timeout=max(0.1, float(settings.redis_socket_timeout)),
            socket_connect_timeout=max(0.1, float(settings.redis_connect_timeout)),
        )
        _redis_client.ping()
    except Exception:  # noqa: BLE001
        _redis_client = None
    return _redis_client


def _loads_safe(raw: str | None) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def load_runtime_config() -> Dict[str, Any]:
    global _cache, _cache_ts
    now = time.monotonic()
    if _cache and (now - _cache_ts) < _CACHE_TTL:
        return _cache

    redis_client = _get_redis_client()
    if redis_client is None:
        _cache_ts = now
        return _cache

    try:
        payload = redis_client.get(_RUNTIME_CONFIG_KEY)
        _cache = _loads_safe(payload)
    except Exception:  # noqa: BLE001
        _cache = _cache or {}
    _cache_ts = now
    return _cache


def save_runtime_config(config: Dict[str, Any]) -> None:
    global _cache, _cache_ts
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            redis_client.set(
                _RUNTIME_CONFIG_KEY,
                json.dumps(config, ensure_ascii=False),
                ex=max(60, int(settings.redis_state_ttl_seconds)),
            )
        except Exception:  # noqa: BLE001
            pass
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
