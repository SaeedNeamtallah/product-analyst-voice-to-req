"""
In-memory cache for latest per-project SRS snapshot.

Design goals:
- Read-through behavior for query-time snapshot retrieval.
- Version-aware synchronization against DB to avoid stale snapshots.
- Easy future replacement with Redis by keeping a narrow API surface.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import logging
import time
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database.models import SRSDraft
from backend.services.redis_keyspace import RedisKeyspace
from backend.services.redis_lock import RedisLockService
from backend.services.redis_runtime import get_redis
from backend.services.runtime_metrics import (
    observe_snapshot_wait,
    record_snapshot_lock_contention,
    record_snapshot_source,
)

logger = logging.getLogger(__name__)


class SRSSnapshotCache:
    """Redis-first cache keyed by project_id for latest SRS snapshot."""

    _COALESCE_NAMESPACE = "srs-snapshot-build"

    @staticmethod
    async def _latest_db_version(db: AsyncSession, project_key: int) -> int | None:
        version_stmt = select(func.max(SRSDraft.version)).where(SRSDraft.project_id == project_key)
        version_result = await db.execute(version_stmt)
        latest_version = version_result.scalar_one_or_none()
        if latest_version is None:
            return None
        try:
            return int(latest_version)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _snapshot_matches_version(snapshot: Dict[str, Any] | None, version: int) -> bool:
        if not snapshot:
            return False
        try:
            return int(snapshot.get("version") or 0) == int(version)
        except (TypeError, ValueError):
            return False

    @classmethod
    async def _wait_for_coalesced_snapshot(
        cls,
        project_key: int,
        latest_version: int,
    ) -> Dict[str, Any] | None:
        started = time.perf_counter()
        for _ in range(8):
            await asyncio.sleep(0.05)
            waited_snapshot = await cls._get_redis_snapshot(project_key)
            if cls._snapshot_matches_version(waited_snapshot, latest_version):
                observe_snapshot_wait(time.perf_counter() - started)
                record_snapshot_source("redis_wait")
                return deepcopy(waited_snapshot)
        observe_snapshot_wait(time.perf_counter() - started)
        return None

    @classmethod
    async def _load_latest_from_db_and_cache(
        cls,
        db: AsyncSession,
        project_key: int,
    ) -> Dict[str, Any] | None:
        latest_stmt = (
            select(SRSDraft)
            .where(SRSDraft.project_id == project_key)
            .order_by(SRSDraft.version.desc(), SRSDraft.created_at.desc())
            .limit(1)
        )
        latest_result = await db.execute(latest_stmt)
        draft = latest_result.scalar_one_or_none()
        if not draft:
            await cls.invalidate(project_key)
            record_snapshot_source("none")
            return None

        snapshot = cls._serialize_draft(draft)
        await cls._set_redis_snapshot(project_key, snapshot)
        record_snapshot_source("db")
        return deepcopy(snapshot)

    @classmethod
    async def _set_redis_snapshot(cls, project_id: int, snapshot: Dict[str, Any]) -> None:
        redis = await get_redis()
        if redis is None:
            return
        try:
            key = RedisKeyspace.srs_snapshot(project_id)
            payload = json.dumps(snapshot, ensure_ascii=False)
            await redis.set(key, payload, ex=max(60, int(settings.redis_draft_ttl_seconds)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to write SRS snapshot to Redis for project %s: %s", project_id, exc)

    @classmethod
    async def _get_redis_snapshot(cls, project_id: int) -> Dict[str, Any] | None:
        redis = await get_redis()
        if redis is None:
            return None
        try:
            key = RedisKeyspace.srs_snapshot(project_id)
            payload = await redis.get(key)
            if not payload:
                return None
            snapshot = json.loads(payload)
            if not isinstance(snapshot, dict):
                return None
            return snapshot
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read SRS snapshot from Redis for project %s: %s", project_id, exc)
            return None

    @classmethod
    async def _delete_redis_snapshot(cls, project_id: int) -> None:
        redis = await get_redis()
        if redis is None:
            return
        try:
            key = RedisKeyspace.srs_snapshot(project_id)
            await redis.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to delete SRS snapshot from Redis for project %s: %s", project_id, exc)

    @classmethod
    def _serialize_draft(cls, draft: SRSDraft) -> Dict[str, Any]:
        content = draft.content if isinstance(draft.content, dict) else {}
        return {
            "version": int(draft.version or 1),
            "status": str(draft.status or "draft"),
            "language": str(draft.language or "ar"),
            "content": deepcopy(content),
        }

    @classmethod
    async def set_from_draft(cls, draft: SRSDraft) -> None:
        """Write-through Redis update from a draft ORM object."""
        if not draft or draft.project_id is None:
            return
        project_id = int(draft.project_id)
        snapshot = cls._serialize_draft(draft)
        await cls._set_redis_snapshot(project_id, snapshot)

    @classmethod
    async def invalidate(cls, project_id: int) -> None:
        project_key = int(project_id)
        await cls._delete_redis_snapshot(project_key)

    @classmethod
    async def get_latest_snapshot(
        cls,
        db: AsyncSession,
        project_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Return the latest SRS snapshot for a project.

        Sync strategy:
        1) Query latest DB version (cheap scalar).
        2) If cache version matches DB version, return cache.
        3) Otherwise load latest draft row, refresh cache, return it.
        """
        project_key = int(project_id)
        redis_snapshot = await cls._get_redis_snapshot(project_key)

        latest_version_int = await cls._latest_db_version(db, project_key)
        if latest_version_int is None:
            await cls.invalidate(project_key)
            record_snapshot_source("none")
            return None

        if cls._snapshot_matches_version(redis_snapshot, latest_version_int):
            record_snapshot_source("redis")
            return deepcopy(redis_snapshot)

        lock_token = await RedisLockService.acquire(
            namespace=cls._COALESCE_NAMESPACE,
            key=str(project_key),
            ttl_seconds=8,
        )

        if lock_token is None:
            record_snapshot_lock_contention()
            waited = await cls._wait_for_coalesced_snapshot(project_key, latest_version_int)
            if waited:
                return waited

        try:
            return await cls._load_latest_from_db_and_cache(db, project_key)
        finally:
            if lock_token:
                await RedisLockService.release(
                    namespace=cls._COALESCE_NAMESPACE,
                    key=str(project_key),
                    token=lock_token,
                )
