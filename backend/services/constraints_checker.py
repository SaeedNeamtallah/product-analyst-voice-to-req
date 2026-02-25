"""
Semantic Evaluator for SRS requirements extraction.

Uses LLM to evaluate ambiguity, contradictions, coverage gaps, scope/budget
risks during the conversation.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from backend.providers.llm.factory import LLMProviderFactory
# Import inside the method to avoid circular imports if any, or just import at top. 
# We'll import at the top for clarity, but interview_service imports constraints_checker.
# Let's import it inside the analyze method to be safe against circular imports.

logger = logging.getLogger(__name__)

class SemanticEvaluation(BaseModel):
    is_ambiguous: bool = Field(description="True if the user's answer is vague or lacks specific details.")
    ambiguity_reason: str = Field(description="Reason for ambiguity, if any.")
    missing_scope_risk: bool = Field(description="True if there is a risk of missing scope or budget constraints.")
    contradiction_detected: bool = Field(description="True if the user's answer contradicts previous statements.")
    contradiction_reason: str = Field(description="Reason for contradiction, if any.")

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
            "Return a JSON object matching the requested schema."
        )
        
        user_prompt = (
            f"Language: {language}\n"
            f"Latest Answer: {answer}\n"
            f"Current Summary: {summary_text}\n"
        )

        try:
            from backend.services.interview_service import InterviewService
            raw_response, _ = await InterviewService._generate_text_resilient(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=500,
                breaker_prefix="semantic_evaluator",
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            try:
                parsed_json = json.loads(raw_response)
                eval_result = SemanticEvaluation(**parsed_json)
            except Exception as e:
                logger.error(f"Failed to parse SemanticEvaluation: {e}")
                eval_result = SemanticEvaluation(
                    is_ambiguous=False,
                    ambiguity_reason="",
                    missing_scope_risk=False,
                    contradiction_detected=False,
                    contradiction_reason=""
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
            logger.error(f"SemanticEvaluator failed: {e}")
            return {
                "ambiguity_detected": False,
                "ambiguity_terms": [],
                "scope_budget_risk": False,
                "contradiction_detected": False,
                "reason": "",
                "low_covered_areas": [],
                "warnings": [],
            }
