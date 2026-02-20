"""
Dynamic slot-filling state machine for SRS requirements extraction.

Runs rule-based analysis on each conversation turn to continuously
fill SRS slots (ambiguity, contradictions, coverage gaps, scope/budget
risks) *during* the conversation rather than at the end.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


class SlotFillingStateMachine:
    """Dynamic state machine that continuously fills SRS requirement slots.

    On every conversation turn it detects ambiguity, contradictions,
    scope/budget risks, and coverage gaps -- feeding the results into
    the interview agent so the SRS JSON is populated incrementally.
    """

    AMBIGUOUS_AR = {"كويس", "قوي", "سريع", "عادي", "كتير", "بسيط", "ممتاز", "احترافي"}
    AMBIGUOUS_EN = {"good", "fast", "strong", "normal", "many", "simple", "best", "powerful", "quick"}
    SCOPE_AR = {"أوبر", "لوحة", "مدفوعات", "متعدد", "لحظي", "داشبورد", "تقارير"}
    SCOPE_EN = {"uber", "marketplace", "real-time", "dashboard", "payments", "multi-tenant", "reports"}
    BUDGET_PATTERN = re.compile(r"\b(\d{2,})(\s?\$|\s?usd|\s?دولار)?\b", re.IGNORECASE)

    @classmethod
    def analyze(
        cls,
        language: str,
        latest_user_answer: str,
        last_summary: Dict[str, Any] | None,
        last_coverage: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        answer = str(latest_user_answer or "").strip()
        lower = answer.lower()
        summary_text = str(last_summary or {}).lower()
        coverage = last_coverage if isinstance(last_coverage, dict) else {}

        ambiguity_terms = cls.AMBIGUOUS_AR if language == "ar" else cls.AMBIGUOUS_EN
        scope_terms = cls.SCOPE_AR if language == "ar" else cls.SCOPE_EN

        ambiguity_hits = [term for term in ambiguity_terms if term in lower]
        scope_hits = [term for term in scope_terms if term in lower]
        budget_hits = cls.BUDGET_PATTERN.findall(answer)

        contradiction_detected = False
        contradiction_reason = ""

        if ("without" in lower or "بدون" in lower) and ("database" in lower or "قاعدة" in lower):
            if "report" in summary_text or "dashboard" in summary_text or "تقارير" in summary_text:
                contradiction_detected = True
                contradiction_reason = (
                    "تعارض: تم طلب تقارير سابقاً مع استبعاد قاعدة البيانات حالياً."
                    if language == "ar"
                    else "Conflict: reports were requested earlier while database is now excluded."
                )

        scope_budget_risk = bool(scope_hits and budget_hits)
        if scope_budget_risk and not contradiction_reason:
            contradiction_reason = (
                "اتساع النطاق مع ميزانية منخفضة قد يهدد تنفيذ MVP."
                if language == "ar"
                else "Broad scope with low budget can threaten MVP feasibility."
            )

        low_areas: List[str] = []
        for area in ("discovery", "scope", "users", "features", "constraints"):
            if float(coverage.get(area, 0) or 0) < 35:
                low_areas.append(area)

        warnings: List[str] = []
        if ambiguity_hits:
            warnings.append(
                "تم رصد عبارات عامة؛ فضّل متطلبات قابلة للقياس."
                if language == "ar"
                else "Generic wording detected; prefer measurable requirements."
            )
        if contradiction_reason:
            warnings.append(contradiction_reason)

        return {
            "ambiguity_detected": bool(ambiguity_hits),
            "ambiguity_terms": ambiguity_hits[:4],
            "scope_budget_risk": scope_budget_risk,
            "contradiction_detected": contradiction_detected,
            "reason": contradiction_reason,
            "low_covered_areas": low_areas[:3],
            "warnings": warnings[:4],
        }
