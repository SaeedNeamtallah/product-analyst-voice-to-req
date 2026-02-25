"""
Telemetry and evaluation metrics for interview agent quality.
"""
from __future__ import annotations

from typing import Any, Dict
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import Project

logger = logging.getLogger(__name__)


class TelemetryService:
    KEY = "agent_telemetry"
    _COUNTER_FIELDS = (
        "interview_turns",
        "ambiguity_detected_count",
        "contradiction_detected_count",
        "ambiguity_cases",
        "ambiguity_resolved",
        "suggestion_offered_turns",
        "suggestion_accepted_count",
    )

    @classmethod
    async def record_interview_turn(
        cls,
        db: AsyncSession,
        project_id: int,
        result: Dict[str, Any],
    ) -> None:
        signals = result.get("signals") if isinstance(result.get("signals"), dict) else {}
        suggested = result.get("suggested_answers") if isinstance(result.get("suggested_answers"), list) else []

        ambiguity_now = bool(signals.get("ambiguity_detected"))
        contradiction_now = bool(signals.get("contradiction_detected"))

        project = await cls._get_project(db, project_id)
        if not project:
            return

        metadata = project.extra_metadata if isinstance(project.extra_metadata, dict) else {}
        telemetry = dict(metadata.get(cls.KEY) or {})
        telemetry.setdefault("interview_turns", 0)
        telemetry.setdefault("ambiguity_detected_count", 0)
        telemetry.setdefault("contradiction_detected_count", 0)
        telemetry.setdefault("ambiguity_cases", 0)
        telemetry.setdefault("ambiguity_resolved", 0)
        telemetry.setdefault("pending_ambiguity", False)
        telemetry.setdefault("suggestion_offered_turns", 0)
        telemetry.setdefault("suggestion_accepted_count", 0)

        telemetry["interview_turns"] += 1
        if ambiguity_now:
            telemetry["ambiguity_detected_count"] += 1
            telemetry["ambiguity_cases"] += 1
            telemetry["pending_ambiguity"] = True
        elif telemetry.get("pending_ambiguity"):
            telemetry["ambiguity_resolved"] += 1
            telemetry["pending_ambiguity"] = False

        if contradiction_now:
            telemetry["contradiction_detected_count"] += 1
        if suggested:
            telemetry["suggestion_offered_turns"] += 1

        metadata = dict(metadata)
        metadata[cls.KEY] = telemetry
        project.extra_metadata = metadata

    @classmethod
    async def record_message_event(
        cls,
        db: AsyncSession,
        project_id: int,
        metadata_payload: Dict[str, Any] | None,
    ) -> None:
        if not isinstance(metadata_payload, dict):
            return
        if not metadata_payload.get("interview_selection"):
            return

        project = await cls._get_project(db, project_id)
        if not project:
            return

        metadata = project.extra_metadata if isinstance(project.extra_metadata, dict) else {}
        telemetry = dict(metadata.get(cls.KEY) or {})
        telemetry.setdefault("suggestion_accepted_count", 0)
        telemetry["suggestion_accepted_count"] += 1

        metadata = dict(metadata)
        metadata[cls.KEY] = telemetry
        project.extra_metadata = metadata

    @classmethod
    async def get_report(cls, db: AsyncSession, project_id: int) -> Dict[str, Any]:
        db_counters = await cls._db_counters(db, project_id)
        if db_counters is None:
            return cls._empty_report()

        turns = int(db_counters.get("interview_turns", 0))
        contradictions = int(db_counters.get("contradiction_detected_count", 0))
        ambiguity_cases = int(db_counters.get("ambiguity_cases", 0))
        ambiguity_resolved = int(db_counters.get("ambiguity_resolved", 0))
        offered = int(db_counters.get("suggestion_offered_turns", 0))
        accepted = int(db_counters.get("suggestion_accepted_count", 0))

        contradiction_catch_rate = round((contradictions / turns) if turns else 0.0, 4)
        ambiguity_resolution_rate = round((ambiguity_resolved / ambiguity_cases) if ambiguity_cases else 0.0, 4)
        suggestion_acceptance_rate = round((accepted / offered) if offered else 0.0, 4)

        return {
            "counters": {
                "interview_turns": turns,
                "contradiction_detected_count": contradictions,
                "ambiguity_cases": ambiguity_cases,
                "ambiguity_resolved": ambiguity_resolved,
                "suggestion_offered_turns": offered,
                "suggestion_accepted_count": accepted,
            },
            "evaluation": {
                "ambiguity_resolution_rate": ambiguity_resolution_rate,
                "contradiction_catch_rate": contradiction_catch_rate,
                "suggestion_acceptance_rate": suggestion_acceptance_rate,
            },
        }

    @classmethod
    async def _db_counters(cls, db: AsyncSession, project_id: int) -> Dict[str, int] | None:
        project = await cls._get_project(db, project_id)
        if not project:
            return None

        metadata = project.extra_metadata if isinstance(project.extra_metadata, dict) else {}
        telemetry = dict(metadata.get(cls.KEY) or {})
        return {
            "interview_turns": int(telemetry.get("interview_turns", 0) or 0),
            "contradiction_detected_count": int(telemetry.get("contradiction_detected_count", 0) or 0),
            "ambiguity_cases": int(telemetry.get("ambiguity_cases", 0) or 0),
            "ambiguity_resolved": int(telemetry.get("ambiguity_resolved", 0) or 0),
            "suggestion_offered_turns": int(telemetry.get("suggestion_offered_turns", 0) or 0),
            "suggestion_accepted_count": int(telemetry.get("suggestion_accepted_count", 0) or 0),
        }

    @staticmethod
    async def _get_project(db: AsyncSession, project_id: int) -> Project | None:
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _empty_report() -> Dict[str, Any]:
        return {
            "counters": {
                "interview_turns": 0,
                "contradiction_detected_count": 0,
                "ambiguity_cases": 0,
                "ambiguity_resolved": 0,
                "suggestion_offered_turns": 0,
                "suggestion_accepted_count": 0,
            },
            "evaluation": {
                "ambiguity_resolution_rate": 0.0,
                "contradiction_catch_rate": 0.0,
                "suggestion_acceptance_rate": 0.0,
            },
        }
