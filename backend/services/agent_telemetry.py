"""
Agent telemetry helpers backed by process-local counters.
"""
from __future__ import annotations

from typing import Any, Dict


class AgentTelemetryService:
    _project_state: dict[int, Dict[str, int | bool]] = {}
    _global_suggestions_accepted: int = 0

    @classmethod
    async def record_turn(
        cls,
        project_id: int,
        signals: Dict[str, Any],
        suggested_answers_count: int,
    ) -> None:
        state = dict(cls._project_state.get(int(project_id), {}))
        state.setdefault("total_turns", 0)
        state.setdefault("ambiguity_detected", 0)
        state.setdefault("ambiguity_resolved", 0)
        state.setdefault("contradiction_risk", 0)
        state.setdefault("contradiction_caught", 0)
        state.setdefault("suggestions_shown", 0)
        state.setdefault("last_ambiguity", False)

        state["total_turns"] = int(state["total_turns"]) + 1

        if bool(signals.get("scope_budget_risk")):
            state["contradiction_risk"] = int(state["contradiction_risk"]) + 1
        if bool(signals.get("contradiction_detected")):
            state["contradiction_caught"] = int(state["contradiction_caught"]) + 1

        ambiguity_now = bool(signals.get("ambiguity_detected"))
        if ambiguity_now:
            state["ambiguity_detected"] = int(state["ambiguity_detected"]) + 1
        if bool(state.get("last_ambiguity")) and not ambiguity_now:
            state["ambiguity_resolved"] = int(state["ambiguity_resolved"]) + 1
        state["last_ambiguity"] = ambiguity_now

        shown = max(0, int(suggested_answers_count))
        if shown > 0:
            state["suggestions_shown"] = int(state["suggestions_shown"]) + shown

        cls._project_state[int(project_id)] = state

    @classmethod
    async def record_suggestion_accepted(cls) -> None:
        cls._global_suggestions_accepted = int(cls._global_suggestions_accepted) + 1

    @classmethod
    async def snapshot(cls, project_id: int) -> Dict[str, Any]:
        state = dict(cls._project_state.get(int(project_id), {}))

        turns = int(state.get("total_turns", 0))
        ambiguity_detected = int(state.get("ambiguity_detected", 0))
        ambiguity_resolved = int(state.get("ambiguity_resolved", 0))
        contradiction_risk = int(state.get("contradiction_risk", 0))
        contradiction_caught = int(state.get("contradiction_caught", 0))
        suggestions_shown = int(state.get("suggestions_shown", 0))
        suggestions_accepted = int(cls._global_suggestions_accepted)

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
