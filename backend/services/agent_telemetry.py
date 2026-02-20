"""
In-memory telemetry for agent quality metrics.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Dict, Any


@dataclass
class TelemetryCounters:
    total_turns: int = 0
    ambiguity_detected: int = 0
    ambiguity_resolved: int = 0
    contradiction_risk: int = 0
    contradiction_caught: int = 0
    suggestions_shown: int = 0
    suggestions_accepted: int = 0


class AgentTelemetryService:
    _lock = Lock()
    _counters = TelemetryCounters()
    _last_ambiguity_by_project: Dict[int, bool] = {}

    @classmethod
    def record_turn(
        cls,
        project_id: int,
        signals: Dict[str, Any],
        suggested_answers_count: int,
    ) -> None:
        with cls._lock:
            cls._counters.total_turns += 1

            contradiction_risk = bool(signals.get("scope_budget_risk"))
            contradiction_caught = bool(signals.get("contradiction_detected"))
            ambiguity = bool(signals.get("ambiguity_detected"))

            if contradiction_risk:
                cls._counters.contradiction_risk += 1
            if contradiction_caught:
                cls._counters.contradiction_caught += 1
            if ambiguity:
                cls._counters.ambiguity_detected += 1

            prev_ambiguity = cls._last_ambiguity_by_project.get(project_id)
            if prev_ambiguity and not ambiguity:
                cls._counters.ambiguity_resolved += 1
            cls._last_ambiguity_by_project[project_id] = ambiguity

            cls._counters.suggestions_shown += max(0, int(suggested_answers_count))

    @classmethod
    def record_suggestion_accepted(cls) -> None:
        with cls._lock:
            cls._counters.suggestions_accepted += 1

    @classmethod
    def snapshot(cls) -> Dict[str, Any]:
        with cls._lock:
            counters = cls._counters
            ambiguity_resolution_rate = (
                counters.ambiguity_resolved / counters.ambiguity_detected
                if counters.ambiguity_detected > 0 else 0.0
            )
            contradiction_catch_rate = (
                counters.contradiction_caught / counters.contradiction_risk
                if counters.contradiction_risk > 0 else 0.0
            )
            suggestion_acceptance_rate = (
                counters.suggestions_accepted / counters.suggestions_shown
                if counters.suggestions_shown > 0 else 0.0
            )

            return {
                "turns": counters.total_turns,
                "ambiguity_resolution_rate": round(ambiguity_resolution_rate, 3),
                "contradiction_catch_rate": round(contradiction_catch_rate, 3),
                "suggestion_acceptance_rate": round(suggestion_acceptance_rate, 3),
                "raw": {
                    "ambiguity_detected": counters.ambiguity_detected,
                    "ambiguity_resolved": counters.ambiguity_resolved,
                    "contradiction_risk": counters.contradiction_risk,
                    "contradiction_caught": counters.contradiction_caught,
                    "suggestions_shown": counters.suggestions_shown,
                    "suggestions_accepted": counters.suggestions_accepted,
                },
            }
