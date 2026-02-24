"""
Redis-backed telemetry for agent quality metrics.
"""
from __future__ import annotations

import logging
from typing import Dict, Any
from datetime import datetime, timezone

from backend.config import settings
from backend.services.redis_keyspace import RedisKeyspace
from backend.services.redis_runtime import get_redis

logger = logging.getLogger(__name__)


class AgentTelemetryService:
    @classmethod
    async def record_turn(
        cls,
        project_id: int,
        signals: Dict[str, Any],
        suggested_answers_count: int,
    ) -> None:
        redis = await get_redis()
        if redis is None:
            return
        key = RedisKeyspace.telemetry_hash(project_id)
        state_key = RedisKeyspace.telemetry_project_state(project_id)

        try:
            await redis.hincrby(key, "total_turns", 1)
            if bool(signals.get("scope_budget_risk")):
                await redis.hincrby(key, "contradiction_risk", 1)
            if bool(signals.get("contradiction_detected")):
                await redis.hincrby(key, "contradiction_caught", 1)

            ambiguity = bool(signals.get("ambiguity_detected"))
            prev_ambiguity_raw = await redis.hget(state_key, "last_ambiguity")
            prev_ambiguity = str(prev_ambiguity_raw or "0") == "1"
            if ambiguity:
                await redis.hincrby(key, "ambiguity_detected", 1)
            if prev_ambiguity and not ambiguity:
                await redis.hincrby(key, "ambiguity_resolved", 1)

            await redis.hset(state_key, mapping={
                "last_ambiguity": "1" if ambiguity else "0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

            shown = max(0, int(suggested_answers_count))
            if shown > 0:
                await redis.hincrby(key, "suggestions_shown", shown)

            ttl = max(60, int(settings.redis_state_ttl_seconds))
            await redis.expire(key, ttl)
            await redis.expire(state_key, ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to record telemetry turn in Redis: %s", exc)

    @classmethod
    async def record_suggestion_accepted(cls) -> None:
        redis = await get_redis()
        if redis is None:
            return
        key = RedisKeyspace.lock("telemetry", "global_suggestions")
        try:
            await redis.hincrby(key, "suggestions_accepted", 1)
            await redis.expire(key, max(60, int(settings.redis_state_ttl_seconds)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to record suggestion acceptance in Redis: %s", exc)

    @classmethod
    async def snapshot(cls, project_id: int) -> Dict[str, Any]:
        redis = await get_redis()
        if redis is None:
            return {
                "turns": 0,
                "ambiguity_resolution_rate": 0.0,
                "contradiction_catch_rate": 0.0,
                "suggestion_acceptance_rate": 0.0,
                "raw": {
                    "ambiguity_detected": 0,
                    "ambiguity_resolved": 0,
                    "contradiction_risk": 0,
                    "contradiction_caught": 0,
                    "suggestions_shown": 0,
                    "suggestions_accepted": 0,
                },
            }

        key = RedisKeyspace.telemetry_hash(project_id)
        global_key = RedisKeyspace.lock("telemetry", "global_suggestions")
        try:
            values = await redis.hgetall(key)
            global_values = await redis.hgetall(global_key)

            def _to_int(name: str, source: Dict[Any, Any]) -> int:
                raw = source.get(name)
                if raw is None:
                    return 0
                try:
                    return int(raw)
                except (TypeError, ValueError):
                    try:
                        return int(raw.decode("utf-8"))
                    except Exception:  # noqa: BLE001
                        return 0

            turns = _to_int("total_turns", values)
            ambiguity_detected = _to_int("ambiguity_detected", values)
            ambiguity_resolved = _to_int("ambiguity_resolved", values)
            contradiction_risk = _to_int("contradiction_risk", values)
            contradiction_caught = _to_int("contradiction_caught", values)
            suggestions_shown = _to_int("suggestions_shown", values)
            suggestions_accepted = _to_int("suggestions_accepted", global_values)

            ambiguity_resolution_rate = (
                ambiguity_resolved / ambiguity_detected if ambiguity_detected > 0 else 0.0
            )
            contradiction_catch_rate = (
                contradiction_caught / contradiction_risk if contradiction_risk > 0 else 0.0
            )
            suggestion_acceptance_rate = (
                suggestions_accepted / suggestions_shown if suggestions_shown > 0 else 0.0
            )

            return {
                "turns": turns,
                "ambiguity_resolution_rate": round(ambiguity_resolution_rate, 3),
                "contradiction_catch_rate": round(contradiction_catch_rate, 3),
                "suggestion_acceptance_rate": round(suggestion_acceptance_rate, 3),
                "raw": {
                    "ambiguity_detected": ambiguity_detected,
                    "ambiguity_resolved": ambiguity_resolved,
                    "contradiction_risk": contradiction_risk,
                    "contradiction_caught": contradiction_caught,
                    "suggestions_shown": suggestions_shown,
                    "suggestions_accepted": suggestions_accepted,
                },
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read telemetry snapshot from Redis: %s", exc)
            return {
                "turns": 0,
                "ambiguity_resolution_rate": 0.0,
                "contradiction_catch_rate": 0.0,
                "suggestion_acceptance_rate": 0.0,
                "raw": {
                    "ambiguity_detected": 0,
                    "ambiguity_resolved": 0,
                    "contradiction_risk": 0,
                    "contradiction_caught": 0,
                    "suggestions_shown": 0,
                    "suggestions_accepted": 0,
                },
            }
