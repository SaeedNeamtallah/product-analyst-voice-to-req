"""
Redis keyspace helpers for shared stateless runtime state.
"""
from __future__ import annotations

from backend.config import settings


class RedisKeyspace:
    """Centralized Redis key builders to prevent key drift across services."""

    @staticmethod
    def _base() -> str:
        return str(settings.redis_key_prefix or "tawasul").strip()

    @classmethod
    def telemetry_hash(cls, project_id: int) -> str:
        return f"{cls._base()}:telemetry:project:{int(project_id)}:counters"

    @classmethod
    def telemetry_project_state(cls, project_id: int) -> str:
        return f"{cls._base()}:telemetry:project:{int(project_id)}:state"

    @classmethod
    def circuit_breaker(cls, breaker_key: str) -> str:
        safe_key = str(breaker_key or "unknown").strip().replace(" ", "_")
        return f"{cls._base()}:cb:{safe_key}"

    @classmethod
    def interview_draft(cls, project_id: int) -> str:
        return f"{cls._base()}:draft:interview:project:{int(project_id)}"

    @classmethod
    def srs_snapshot(cls, project_id: int) -> str:
        return f"{cls._base()}:srs:snapshot:project:{int(project_id)}"

    @classmethod
    def telegram_session(cls, chat_id: int) -> str:
        return f"{cls._base()}:telegram:session:chat:{int(chat_id)}"

    @classmethod
    def lock(cls, namespace: str, key: str) -> str:
        ns = str(namespace or "global").strip().replace(" ", "_")
        safe_key = str(key or "default").strip().replace(" ", "_")
        return f"{cls._base()}:lock:{ns}:{safe_key}"
