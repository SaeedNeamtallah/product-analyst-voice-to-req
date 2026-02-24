"""
Shared resilience helpers: Redis-backed circuit breaker and async failover execution.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Iterable, Optional, Tuple
import logging
import time

from backend.config import settings
from backend.services.redis_keyspace import RedisKeyspace
from backend.services.redis_runtime import get_redis
from backend.services.runtime_metrics import record_cb_event, record_cb_open_check

logger = logging.getLogger(__name__)

_CB_IS_OPEN_SCRIPT = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local ttl_sec = tonumber(ARGV[2])
local opened_until_ms = tonumber(redis.call('HGET', key, 'opened_until_ms') or '0')
if opened_until_ms > now_ms then
    return 1
end
if opened_until_ms > 0 then
    redis.call('HSET', key, 'failures', 0, 'opened_until_ms', 0)
    redis.call('EXPIRE', key, ttl_sec)
end
return 0
"""

_CB_RECORD_FAILURE_SCRIPT = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local threshold = tonumber(ARGV[2])
local cooldown_ms = tonumber(ARGV[3])
local ttl_sec = tonumber(ARGV[4])
local opened_until_ms = tonumber(redis.call('HGET', key, 'opened_until_ms') or '0')
if opened_until_ms > now_ms then
    return {0, tonumber(redis.call('HGET', key, 'failures') or '0'), opened_until_ms}
end
local failures = tonumber(redis.call('HGET', key, 'failures') or '0')
failures = failures + 1
if failures >= threshold then
    opened_until_ms = now_ms + cooldown_ms
else
    opened_until_ms = 0
end
redis.call('HSET', key, 'failures', failures, 'opened_until_ms', opened_until_ms)
redis.call('EXPIRE', key, ttl_sec)
return {1, failures, opened_until_ms}
"""

class CircuitBreakerRegistry:
    """Redis-backed circuit breaker registry."""

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _group(key: str) -> str:
        return str(key or "unknown").split(":", 1)[0]

    async def _get_redis_state(self, key: str) -> tuple[int, datetime | None] | None:
        redis = await get_redis()
        if redis is None:
            return None
        try:
            redis_key = RedisKeyspace.circuit_breaker(key)
            values = await redis.hgetall(redis_key)
            if not values:
                return 0, None
            try:
                failures = int(values.get("failures", "0"))
            except (TypeError, ValueError):
                failures = 0
            raw_ms = values.get("opened_until_ms", "0")
            try:
                opened_until_ms = int(raw_ms)
            except (TypeError, ValueError):
                opened_until_ms = 0
            opened_until = (
                datetime.fromtimestamp(opened_until_ms / 1000.0, tz=timezone.utc)
                if opened_until_ms > 0
                else None
            )
            return failures, opened_until
        except Exception as exc:  # noqa: BLE001
            logger.warning("Circuit breaker Redis read failed for %s: %s", key, exc)
            return None

    async def _set_redis_state(self, key: str, failures: int, opened_until: datetime | None) -> None:
        redis = await get_redis()
        if redis is None:
            return
        try:
            redis_key = RedisKeyspace.circuit_breaker(key)
            opened_until_ms = int(opened_until.timestamp() * 1000) if opened_until else 0
            mapping = {
                "failures": str(max(0, int(failures))),
                "opened_until_ms": str(max(0, opened_until_ms)),
            }
            await redis.hset(redis_key, mapping=mapping)
            await redis.expire(redis_key, max(60, int(settings.redis_state_ttl_seconds)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Circuit breaker Redis write failed for %s: %s", key, exc)

    async def is_open(self, key: str) -> bool:
        redis = await get_redis()
        if redis is not None:
            try:
                redis_key = RedisKeyspace.circuit_breaker(key)
                result = await redis.eval(
                    _CB_IS_OPEN_SCRIPT,
                    1,
                    redis_key,
                    str(self._now_ms()),
                    str(max(60, int(settings.redis_state_ttl_seconds))),
                )
                is_open = int(result or 0) == 1
                record_cb_open_check(self._group(key), is_open)
                return is_open
            except Exception as exc:  # noqa: BLE001
                logger.warning("Circuit breaker atomic open-check failed for %s: %s", key, exc)

        record_cb_open_check(self._group(key), False)
        return False

    async def record_success(self, key: str) -> None:
        await self._set_redis_state(key, 0, None)
        record_cb_event(self._group(key), "success")

    async def record_failure(self, key: str, threshold: int = 3, cooldown_seconds: int = 45) -> None:
        redis = await get_redis()
        if redis is not None:
            try:
                redis_key = RedisKeyspace.circuit_breaker(key)
                result = await redis.eval(
                    _CB_RECORD_FAILURE_SCRIPT,
                    1,
                    redis_key,
                    str(self._now_ms()),
                    str(max(1, int(threshold))),
                    str(max(1, int(cooldown_seconds)) * 1000),
                    str(max(60, int(settings.redis_state_ttl_seconds))),
                )
                opened_until_ms = 0
                if isinstance(result, (list, tuple)) and len(result) >= 3:
                    try:
                        opened_until_ms = int(result[2] or 0)
                    except (TypeError, ValueError):
                        opened_until_ms = 0
                record_cb_event(self._group(key), "failure")
                if opened_until_ms > self._now_ms():
                    record_cb_event(self._group(key), "opened")
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Circuit breaker atomic failure-record failed for %s: %s", key, exc)
        record_cb_event(self._group(key), "failure")


circuit_breakers = CircuitBreakerRegistry()


async def run_with_failover(
    providers: Iterable[Tuple[str, Callable[[], Awaitable[Any]]]],
    *,
    breaker_prefix: str,
    failure_threshold: int = 3,
    cooldown_seconds: int = 45,
) -> Tuple[Any, str]:
    """Try providers in order with circuit-breaker short-circuiting.

    Returns tuple of (result, provider_name).
    Raises RuntimeError with aggregated failure reason if all fail.
    """
    last_error: Optional[Exception] = None

    for provider_name, call in providers:
        key = f"{breaker_prefix}:{provider_name}"
        if await circuit_breakers.is_open(key):
            continue
        try:
            result = await call()
            await circuit_breakers.record_success(key)
            return result, provider_name
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            error_text = str(exc).lower()
            is_rate_limited = (
                "429" in error_text
                or "quota exceeded" in error_text
                or "rate limit" in error_text
                or "too many requests" in error_text
            )
            effective_threshold = 1 if is_rate_limited else failure_threshold
            effective_cooldown = max(cooldown_seconds, 180) if is_rate_limited else cooldown_seconds
            await circuit_breakers.record_failure(
                key,
                threshold=effective_threshold,
                cooldown_seconds=effective_cooldown,
            )

    if last_error is None:
        raise RuntimeError("No available providers (all circuit breakers are open)")
    raise RuntimeError(f"All providers failed: {last_error}")
