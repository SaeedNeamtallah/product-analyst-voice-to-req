"""
Semantic Evaluator for SRS requirements extraction.

Uses LLM to evaluate ambiguity, contradictions, coverage gaps, scope/budget
risks during the conversation.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class SemanticEvaluation(BaseModel):
    is_ambiguous: bool = Field(description="True if the user's answer is vague or lacks specific details.")
    ambiguity_reason: str = Field(description="Reason for ambiguity, if any.")
    missing_scope_risk: bool = Field(description="True if there is a risk of missing scope or budget constraints.")
    contradiction_detected: bool = Field(description="True if the user's answer contradicts previous statements.")
    contradiction_reason: str = Field(description="Reason for contradiction, if any.")

    @model_validator(mode="before")
    @classmethod
    def _unwrap_and_normalise(cls, data: Any) -> Any:
        """
        The LLM sometimes wraps its output in a top-level key like:
            {"evaluation": {"ambiguity": ..., "is_ambiguous": ..., ...}}
        or uses slightly different field names.  This validator:
          1. Unwraps any single-key envelope (evaluation / result / data / response).
          2. Maps common LLM field aliases to the canonical field names.
        """
        if not isinstance(data, dict):
            return data

        # ── 1. Unwrap envelope ────────────────────────────────────────────────
        ENVELOPE_KEYS = {"evaluation", "result", "data", "response", "output"}
        if len(data) == 1:
            only_key = next(iter(data))
            if only_key.lower() in ENVELOPE_KEYS and isinstance(data[only_key], dict):
                data = data[only_key]

        # ── 2. Alias map ──────────────────────────────────────────────────────
        # Maps whatever the LLM may send → canonical field name
        ALIASES: Dict[str, str] = {
            # is_ambiguous
            "ambiguous": "is_ambiguous",
            "ambiguity": "is_ambiguous",
            "is_vague": "is_ambiguous",
            # ambiguity_reason
            "ambiguity_details": "ambiguity_reason",
            "ambiguity_explanation": "ambiguity_reason",
            "vagueness_reason": "ambiguity_reason",
            "reason_for_ambiguity": "ambiguity_reason",
            # missing_scope_risk
            "scope_risk": "missing_scope_risk",
            "budget_risk": "missing_scope_risk",
            "scope_budget_risk": "missing_scope_risk",
            "has_scope_risk": "missing_scope_risk",
            # contradiction_detected
            "contradiction": "contradiction_detected",
            "has_contradiction": "contradiction_detected",
            "contradicts": "contradiction_detected",
            # contradiction_reason
            "contradiction_details": "contradiction_reason",
            "contradiction_explanation": "contradiction_reason",
            "reason_for_contradiction": "contradiction_reason",
        }

        normalised: Dict[str, Any] = {}
        for k, v in data.items():
            canonical = ALIASES.get(k.lower(), k)
            normalised[canonical] = v

        # ── 3. Fill safe defaults for any still-missing required fields ───────
        normalised.setdefault("is_ambiguous", False)
        normalised.setdefault("ambiguity_reason", "")
        normalised.setdefault("missing_scope_risk", False)
        normalised.setdefault("contradiction_detected", False)
        normalised.setdefault("contradiction_reason", "")

        return normalised


class SemanticEvaluator:
    """LLM-based evaluator for semantic reasoning of user inputs."""

    @classmethod
    async def analyze(
        cls,
        language: str,
        latest_user_answer: str,
        last_summary: Dict[str, Any] | None,
        last_coverage: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        answer = str(latest_user_answer or "").strip()
        summary_text = json.dumps(last_summary or {}, ensure_ascii=False)

        system_prompt = (
            "You are an expert business analyst evaluating a user's response for a software project requirements gathering interview.\n"
            "Evaluate the user's latest answer against the current summary for ambiguity, scope risks, and contradictions.\n"
            "CRITICAL: Base your evaluation STRICTLY on the provided text. Do not invent context or hallucinate contradictions that do not exist in the text.\n"
            "Return a FLAT JSON object with exactly these keys (no nesting, no wrapper):\n"
            "  is_ambiguous        (bool)\n"
            "  ambiguity_reason    (string)\n"
            "  missing_scope_risk  (bool)\n"
            "  contradiction_detected (bool)\n"
            "  contradiction_reason   (string)"
        )

        user_prompt = (
            f"Language: {language}\n"
            f"Latest Answer: {answer}\n"
            f"Current Summary: {summary_text}\n"
        )

        try:
            from backend.services.interview_service import InterviewService  # avoid circular import
            raw_response, _ = await InterviewService._generate_text_resilient(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=500,
                breaker_prefix="semantic_evaluator",
                response_format={"type": "json_object"},
            )

            try:
                parsed_json = json.loads(raw_response)
                eval_result = SemanticEvaluation(**parsed_json)
            except Exception as e:
                logger.error("Failed to parse SemanticEvaluation: %s", e)
                eval_result = SemanticEvaluation(
                    is_ambiguous=False,
                    ambiguity_reason="",
                    missing_scope_risk=False,
                    contradiction_detected=False,
                    contradiction_reason="",
                )

            low_areas: List[str] = []
            coverage = last_coverage if isinstance(last_coverage, dict) else {}
            for area in ("discovery", "scope", "users", "features", "constraints"):
                if float(coverage.get(area, 0) or 0) < 35:
                    low_areas.append(area)

            warnings: List[str] = []
            if eval_result.is_ambiguous and eval_result.ambiguity_reason:
                warnings.append(eval_result.ambiguity_reason)
            if eval_result.contradiction_detected and eval_result.contradiction_reason:
                warnings.append(eval_result.contradiction_reason)

            return {
                "ambiguity_detected": eval_result.is_ambiguous,
                "ambiguity_terms": [eval_result.ambiguity_reason] if eval_result.is_ambiguous else [],
                "scope_budget_risk": eval_result.missing_scope_risk,
                "contradiction_detected": eval_result.contradiction_detected,
                "reason": eval_result.contradiction_reason,
                "low_covered_areas": low_areas[:3],
                "warnings": warnings[:4],
            }

        except Exception as e:
            logger.error("SemanticEvaluator failed: %s", e)
            return {
                "ambiguity_detected": False,
                "ambiguity_terms": [],
                "scope_budget_risk": False,
                "contradiction_detected": False,
                "reason": "",
                "low_covered_areas": [],
                "warnings": [],
            }