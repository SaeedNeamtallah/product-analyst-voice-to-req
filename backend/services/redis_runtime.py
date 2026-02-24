"""
Async Redis runtime client and lifecycle helpers.
"""
from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Optional

from redis.asyncio import Redis

from backend.config import settings
from backend.services.runtime_metrics import set_redis_up, record_redis_unavailable

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None
_init_lock = asyncio.Lock()


def redis_enabled() -> bool:
    return bool(settings.redis_enabled and str(settings.redis_url or "").strip())


async def get_redis() -> Optional[Redis]:
    """Get a singleton async Redis client (lazy-initialized)."""
    global _redis_client

    if not redis_enabled():
        set_redis_up(False)
        record_redis_unavailable("disabled")
        return None

    if _redis_client is not None:
        return _redis_client

    async with _init_lock:
        if _redis_client is not None:
            return _redis_client

        try:
            cert_req_mode = str(settings.redis_ssl_cert_reqs or "required").strip().lower()
            cert_reqs = {
                "required": ssl.CERT_REQUIRED,
                "optional": ssl.CERT_OPTIONAL,
                "none": ssl.CERT_NONE,
            }.get(cert_req_mode, ssl.CERT_REQUIRED)

            redis_url = str(settings.redis_url)
            use_ssl = bool(settings.redis_require_tls or redis_url.startswith("rediss://"))

            client_kwargs = {
                "encoding": "utf-8",
                "decode_responses": True,
                "max_connections": max(10, int(settings.redis_max_connections)),
                "socket_timeout": max(0.1, float(settings.redis_socket_timeout)),
                "socket_connect_timeout": max(0.1, float(settings.redis_connect_timeout)),
                "health_check_interval": max(1, int(settings.redis_health_check_interval)),
            }
            if use_ssl:
                client_kwargs["ssl"] = True
                client_kwargs["ssl_cert_reqs"] = cert_reqs

            if str(settings.redis_username or "").strip():
                client_kwargs["username"] = str(settings.redis_username).strip()
            if str(settings.redis_password or "").strip():
                client_kwargs["password"] = str(settings.redis_password).strip()

            _redis_client = Redis.from_url(
                redis_url,
                **client_kwargs,
            )
            await _redis_client.ping()
            logger.info("Redis connected successfully")
            set_redis_up(True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis unavailable, continuing without Redis shared state: %s", exc)
            set_redis_up(False)
            record_redis_unavailable("connect_error")
            _redis_client = None

    return _redis_client


async def close_redis() -> None:
    """Close Redis client pool on application shutdown."""
    global _redis_client
    if _redis_client is None:
        return

    try:
        await _redis_client.aclose()
        logger.info("Redis connections closed")
        set_redis_up(False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to close Redis cleanly: %s", exc)
        set_redis_up(False)
        record_redis_unavailable("close_error")
    finally:
        _redis_client = None
