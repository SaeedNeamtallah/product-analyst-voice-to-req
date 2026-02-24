"""
Distributed Redis lock helper.
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from backend.services.redis_keyspace import RedisKeyspace
from backend.services.redis_runtime import get_redis
from backend.services.runtime_metrics import record_redis_lock_attempt, observe_redis_lock_wait

_RELEASE_LOCK_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
else
  return 0
end
"""


class RedisLockService:
    @classmethod
    async def acquire(
        cls,
        *,
        namespace: str,
        key: str,
        ttl_seconds: int = 8,
    ) -> Optional[str]:
        started = time.perf_counter()
        redis = await get_redis()
        if redis is None:
            record_redis_lock_attempt(namespace, acquired=False)
            observe_redis_lock_wait(namespace, time.perf_counter() - started)
            return None

        lock_key = RedisKeyspace.lock(namespace, key)
        token = uuid.uuid4().hex
        acquired = await redis.set(lock_key, token, nx=True, ex=max(1, int(ttl_seconds)))
        record_redis_lock_attempt(namespace, acquired=bool(acquired))
        observe_redis_lock_wait(namespace, time.perf_counter() - started)
        if acquired:
            return token
        return None

    @classmethod
    async def release(
        cls,
        *,
        namespace: str,
        key: str,
        token: str,
    ) -> None:
        redis = await get_redis()
        if redis is None:
            return

        lock_key = RedisKeyspace.lock(namespace, key)
        await redis.eval(_RELEASE_LOCK_SCRIPT, 1, lock_key, str(token))
