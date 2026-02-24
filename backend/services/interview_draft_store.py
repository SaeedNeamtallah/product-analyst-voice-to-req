"""
Redis-backed interview draft store.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from backend.config import settings
from backend.services.redis_keyspace import RedisKeyspace
from backend.services.redis_runtime import get_redis

logger = logging.getLogger(__name__)


class InterviewDraftStore:
    """Shared interview draft state across workers via Redis."""

    @classmethod
    async def get(cls, project_id: int) -> Optional[Dict[str, Any]]:
        redis = await get_redis()
        if redis is None:
            return None
        try:
            key = RedisKeyspace.interview_draft(project_id)
            payload = await redis.get(key)
            if not payload:
                return None
            draft = json.loads(payload)
            return draft if isinstance(draft, dict) else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read interview draft from Redis for project %s: %s", project_id, exc)
            return None

    @classmethod
    async def set(cls, project_id: int, draft: Dict[str, Any]) -> None:
        redis = await get_redis()
        if redis is None:
            return
        try:
            key = RedisKeyspace.interview_draft(project_id)
            payload = json.dumps(draft, ensure_ascii=False)
            await redis.set(key, payload, ex=max(60, int(settings.redis_draft_ttl_seconds)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to write interview draft to Redis for project %s: %s", project_id, exc)

    @classmethod
    async def delete(cls, project_id: int) -> None:
        redis = await get_redis()
        if redis is None:
            return
        try:
            key = RedisKeyspace.interview_draft(project_id)
            await redis.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to delete interview draft from Redis for project %s: %s", project_id, exc)
