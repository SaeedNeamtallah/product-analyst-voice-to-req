"""
Live SRS patch builder for all chat flows (not interview-only).
"""
from __future__ import annotations

import json
import logging
from uuid import uuid4
from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationError

from backend.database.models import ChatMessage
from backend.providers.llm.factory import LLMProviderFactory
from backend.services.constraints_checker import SemanticEvaluator
from backend.services.interview_service import InterviewService

logger = logging.getLogger(__name__)

_AREAS = ["discovery", "scope", "users", "features", "constraints"]


class LivePatchExtraction(BaseModel):
    summary: Dict[str, List[str]]
    coverage: Dict[str, float]
    target_stage: str = Field(pattern="^(discovery|scope|users|features|constraints)$")


class LivePatchService:
    """Builds cumulative summary/coverage + structured patch events from chat history."""

    @classmethod
    async def build_from_messages(
        cls,
        language: str,
        messages: List[ChatMessage],
        last_summary: Dict[str, Any] | None,
        last_coverage: Dict[str, float] | None,
    ) -> Dict[str, Any]:
        old_summary = InterviewService._normalized_summary(last_summary)
        old_coverage = last_coverage if isinstance(last_coverage, dict) else {}

        extracted = await cls._extract_semantic_state(
            language=language,
            messages=messages,
            old_summary=old_summary,
            old_coverage=old_coverage,
        )

        new_summary = cls._merge_summary(old_summary, extracted.get("summary") or {})
        new_coverage = cls._merge_coverage(extracted.get("coverage") or {}, old_coverage)
        stage = extracted.get("target_stage") or InterviewService._pick_focus_area(new_coverage)

        latest_user = ""
        for msg in reversed(messages):
            if str(msg.role or "").lower() == "user":
                latest_user = str(msg.content or "").strip()
                break

        slot_analysis = await SemanticEvaluator.analyze(
            language=language,
            latest_user_answer=latest_user,
            last_summary=new_summary,
            last_coverage=old_coverage,
        )
        reflector_signals = cls._signals_from_semantic(
            slot_analysis=slot_analysis,
            coverage=new_coverage,
            target_stage=stage,
        )

        doc_patch = InterviewService._build_documentation_patch(
            language=language,
            stage=stage,
            new_summary=new_summary,
            old_summary=old_summary,
            new_coverage=new_coverage,
            old_coverage=old_coverage,
            reflector_signals=reflector_signals,
        )

        cycle_trace = InterviewService._build_cycle_trace(
            language=language,
            stage=stage,
            reflector_signals=reflector_signals,
            coverage=new_coverage,
            doc_patch=doc_patch,
        )
        topic_navigation = InterviewService._build_topic_navigation(
            language=language,
            summary=new_summary,
            coverage=new_coverage,
            reflector_signals=reflector_signals,
        )

        return {
            "stage": stage,
            "summary": new_summary,
            "coverage": new_coverage,
            "signals": reflector_signals,
            "live_patch": doc_patch,
            "cycle_trace": cycle_trace,
            "topic_navigation": topic_navigation,
        }

    @classmethod
    async def _extract_semantic_state(
        cls,
        *,
        language: str,
        messages: List[ChatMessage],
        old_summary: Dict[str, Any],
        old_coverage: Dict[str, float],
    ) -> Dict[str, Any]:
        conversation = cls._render_conversation(messages[-40:])
        system_prompt = (
            "You are an enterprise requirements analyst. "
            "Extract semantic project state from conversation and return strict JSON."
        )
        user_prompt = (
            f"Language: {language}\n"
            f"Previous summary: {json.dumps(old_summary, ensure_ascii=False)}\n"
            f"Previous coverage: {json.dumps(old_coverage, ensure_ascii=False)}\n"
            f"Conversation:\n{conversation}\n\n"
            "Return JSON with keys: summary, coverage, target_stage.\n"
            "summary must contain discovery/scope/users/features/constraints as arrays of short concrete requirements.\n"
            "coverage values must be 0..100."
        )

        provider = LLMProviderFactory.create_provider()
        try:
            raw = await provider.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=1800,
                response_format={"type": "json_object"},
            )
            parsed = LivePatchExtraction.model_validate_json(raw)
            return {
                "summary": parsed.summary,
                "coverage": parsed.coverage,
                "target_stage": parsed.target_stage,
            }
        except ValidationError as exc:
            logger.warning("Live patch extraction schema validation failed: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Live patch semantic extraction failed: %s", exc)

        return {
            "summary": {area: [] for area in _AREAS},
            "coverage": old_coverage,
            "target_stage": InterviewService._pick_focus_area(old_coverage),
        }

    @staticmethod
    def _render_conversation(messages: List[ChatMessage]) -> str:
        lines: List[str] = []
        for msg in messages:
            role = str(msg.role or "system").lower()
            if role not in {"user", "assistant", "system"}:
                role = "system"
            content = str(msg.content or "").strip()
            if not content:
                continue
            lines.append(f"{role}: {content[:900]}")
        return "\n".join(lines)

    @staticmethod
    def _merge_summary(
        old_summary: Dict[str, Any],
        extracted_summary: Dict[str, List[str]],
    ) -> Dict[str, List[Dict[str, str]]]:
        merged = InterviewService._normalized_summary(old_summary)
        for area in _AREAS:
            values = extracted_summary.get(area) if isinstance(extracted_summary.get(area), list) else []
            for value in values:
                text = str(value or "").strip()
                if not text:
                    continue
                existing = merged.get(area, [])
                if InterviewService._contains_similar_requirement(existing, text):
                    continue
                existing.append({"id": f"req_{uuid4().hex[:12]}", "value": text})
                merged[area] = existing[:24]
        return merged

    @staticmethod
    def _merge_coverage(new_cov: Dict[str, Any], old_cov: Dict[str, float]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for area in _AREAS:
            try:
                new_value = float(new_cov.get(area, 0) or 0)
            except (TypeError, ValueError):
                new_value = 0.0
            prev = float(old_cov.get(area, 0) or 0)
            out[area] = round(max(0.0, min(100.0, max(prev, new_value))), 2)
        return out

    @staticmethod
    def _signals_from_semantic(
        *,
        slot_analysis: Dict[str, Any],
        coverage: Dict[str, float],
        target_stage: str,
    ) -> Dict[str, Any]:
        reason = str(slot_analysis.get("reason") or "").strip()
        ambiguity = bool(slot_analysis.get("ambiguity_detected"))
        contradiction = bool(slot_analysis.get("contradiction_detected"))
        scope_budget_risk = bool(slot_analysis.get("scope_budget_risk"))
        low_covered_areas = [area for area in _AREAS if float(coverage.get(area, 0) or 0) < 35][:3]

        question_style = "inference-driven"
        if contradiction or scope_budget_risk:
            question_style = "resolve-conflict"
        elif ambiguity:
            question_style = "clarify-ambiguity"

        return {
            "ambiguity_detected": ambiguity,
            "ambiguity_terms": slot_analysis.get("ambiguity_terms") if isinstance(slot_analysis.get("ambiguity_terms"), list) else [],
            "scope_budget_risk": scope_budget_risk,
            "contradiction_detected": contradiction,
            "reason": reason,
            "recommendation": reason,
            "low_covered_areas": low_covered_areas,
            "question_style": question_style,
            "target_stage": target_stage if target_stage in _AREAS else InterviewService._pick_focus_area(coverage),
            "slot_analysis": slot_analysis,
        }
