"""
In-memory cache for latest per-project SRS snapshot.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import SRSDraft
from backend.services.runtime_metrics import record_snapshot_source


class SRSSnapshotCache:
    """In-memory snapshot cache keyed by project_id for latest SRS snapshot."""

    _cache: dict[int, Dict[str, Any]] = {}
    _locks: dict[int, asyncio.Lock] = {}

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
    def _serialize_draft(cls, draft: SRSDraft) -> Dict[str, Any]:
        content = draft.content if isinstance(draft.content, dict) else {}
        return {
            "version": int(draft.version or 1),
            "status": str(draft.status or "draft"),
            "language": str(draft.language or "ar"),
            "content": deepcopy(content),
        }

    @classmethod
    async def _load_latest_from_db(cls, db: AsyncSession, project_key: int) -> Dict[str, Any] | None:
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
        cls._cache[project_key] = deepcopy(snapshot)
        record_snapshot_source("db")
        return deepcopy(snapshot)

    @classmethod
    async def set_from_draft(cls, draft: SRSDraft) -> None:
        if not draft or draft.project_id is None:
            return
        project_id = int(draft.project_id)
        cls._cache[project_id] = cls._serialize_draft(draft)

    @classmethod
    async def invalidate(cls, project_id: int) -> None:
        project_key = int(project_id)
        cls._cache.pop(project_key, None)

    @classmethod
    async def get_latest_snapshot(
        cls,
        db: AsyncSession,
        project_id: int,
    ) -> Optional[Dict[str, Any]]:
        project_key = int(project_id)
        cached_snapshot = cls._cache.get(project_key)

        latest_version_int = await cls._latest_db_version(db, project_key)
        if latest_version_int is None:
            await cls.invalidate(project_key)
            record_snapshot_source("none")
            return None

        if cls._snapshot_matches_version(cached_snapshot, latest_version_int):
            record_snapshot_source("cache")
            return deepcopy(cached_snapshot)

        lock = cls._locks.setdefault(project_key, asyncio.Lock())
        async with lock:
            cached_snapshot = cls._cache.get(project_key)
            if cls._snapshot_matches_version(cached_snapshot, latest_version_int):
                record_snapshot_source("cache")
                return deepcopy(cached_snapshot)
            return await cls._load_latest_from_db(db, project_key)
