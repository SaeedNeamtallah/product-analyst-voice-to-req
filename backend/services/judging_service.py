from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import SRSDraft
from backend.providers.llm.factory import LLMProviderFactory

logger = logging.getLogger(__name__)


class JudgingService:
    """
    Standalone Judging Service for verifying, critiquing, and refining SRS.
    Runs three parallel critique agents (technical + business), then refines
    the SRS and produces an executive summary.

    Author: Adel Sobhy
    Date: 2026-02-15
    """

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider or LLMProviderFactory.create_provider()
        logger.info("Judging service initialized")

    async def judge_and_refine(
        self,
        srs_content: Dict[str, Any],
        language: str = "ar",
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Judge SRS, refine it, generate summary, and return result dict."""
        logger.info("Starting judgment for project %s (lang=%s)", project_id, language)

        # 1. Parallel critiques
        tech_critique = await self._get_technical_critique(srs_content, language)
        biz_critique  = await self._get_business_critique(srs_content, language)

        # 2. Refine SRS using both critiques
        refined_srs = await self._refine_srs(srs_content, tech_critique, biz_critique, language)

        # 3. Executive summary of the judging round
        summary = await self._generate_summary(tech_critique, biz_critique, language)

        return {
            "technical_critique": tech_critique,
            "business_critique":  biz_critique,
            "refined_srs":        refined_srs,
            "summary":            summary,
            "timestamp":          datetime.utcnow().isoformat(),
        }

    # ─────────────────────────── agent methods ────────────────────────────

    async def _get_technical_critique(
        self, srs_content: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        prompt = self._build_technical_critique_prompt(srs_content, language)
        raw    = await self.llm_provider.generate_text(
            prompt=prompt, temperature=0.3, max_tokens=3000
        )
        result = self._extract_json(raw)
        if result is None:
            logger.warning("Technical critique JSON extraction failed.")
            return {"error": "Technical critique failed", "raw": raw[:500]}
        return result

    async def _get_business_critique(
        self, srs_content: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        prompt = self._build_business_critique_prompt(srs_content, language)
        raw    = await self.llm_provider.generate_text(
            prompt=prompt, temperature=0.3, max_tokens=3000
        )
        result = self._extract_json(raw)
        if result is None:
            logger.warning("Business critique JSON extraction failed.")
            return {"error": "Business critique failed", "raw": raw[:500]}
        return result

    async def _refine_srs(
        self,
        srs_content: Dict[str, Any],
        tech: Dict[str, Any],
        biz: Dict[str, Any],
        language: str,
    ) -> Dict[str, Any]:
        prompt  = self._build_srs_refinement_prompt(srs_content, tech, biz, language)
        raw     = await self.llm_provider.generate_text(
            prompt=prompt, temperature=0.2, max_tokens=4000
        )
        refined = self._extract_json(raw)

        if not refined:
            logger.warning("Refinement produced no JSON — returning original SRS.")
            return srs_content

        required_keys = {"summary", "metrics", "sections", "questions", "next_steps"}
        missing = required_keys - set(refined.keys())
        if missing:
            logger.warning(
                "Refined SRS is missing keys %s — returning original SRS.", missing
            )
            return srs_content

        # Sanity-check: sections must be a non-empty list
        if not isinstance(refined.get("sections"), list) or not refined["sections"]:
            logger.warning("Refined SRS has empty/invalid sections — returning original SRS.")
            return srs_content

        return refined

    async def _generate_summary(
        self,
        tech: Dict[str, Any],
        biz: Dict[str, Any],
        language: str,
    ) -> Dict[str, Any]:
        prompt = self._build_summary_prompt(tech, biz, language)
        raw    = await self.llm_provider.generate_text(
            prompt=prompt, temperature=0.4, max_tokens=2000
        )
        result = self._extract_json(raw)
        if result is None:
            logger.warning("Summary generation JSON extraction failed.")
            return {"status": "Summary generation failed", "raw": raw[:500]}
        return result

    # ──────────────────────────── prompt builders ─────────────────────────

    def _build_technical_critique_prompt(
        self, srs_content: Dict[str, Any], language: str
    ) -> str:
        srs_json = json.dumps(srs_content, ensure_ascii=False, indent=2)
        schema   = '{"strengths": [], "weaknesses": [], "risks": [], "recommendations": []}'
        if language == "ar":
            return (
                f"أنت كبير مهندسي البرمجيات (CTO). قيم هذا المستند تقنياً.\n"
                f"المستند:\n{srs_json}\n\n"
                f"ركز على: المعمارية، الأداء، الأمان، والتدرج.\n"
                f"أجب بصيغة JSON فقط: {schema}"
            )
        return (
            f"You are a CTO/Senior Architect. Find technical flaws in this SRS.\n"
            f"SRS:\n{srs_json}\n\n"
            f"Focus on Architecture, Performance, Security, Scalability.\n"
            f"Return ONLY JSON: {schema}"
        )

    def _build_business_critique_prompt(
        self, srs_content: Dict[str, Any], language: str
    ) -> str:
        srs_json = json.dumps(srs_content, ensure_ascii=False, indent=2)
        schema   = '{"strengths": [], "weaknesses": [], "risks": [], "recommendations": []}'
        if language == "ar":
            return (
                f"أنت محلل أعمال أول. قيّم هذا المستند من المنظور التجاري.\n"
                f"المستند:\n{srs_json}\n\n"
                f"ركز على: قيمة الأعمال، وضوح المتطلبات، اتساق النطاق، وجاهزية السوق.\n"
                f"أجب بصيغة JSON فقط: {schema}"
            )
        return (
            f"You are a Senior Business Analyst. Evaluate this SRS from a business perspective.\n"
            f"SRS:\n{srs_json}\n\n"
            f"Focus on: business value, requirements clarity, scope consistency, market readiness.\n"
            f"Return ONLY JSON: {schema}"
        )

    def _build_srs_refinement_prompt(
        self,
        srs_content: Dict[str, Any],
        tech: Dict[str, Any],
        biz: Dict[str, Any],
        language: str,
    ) -> str:
        srs_json  = json.dumps(srs_content, ensure_ascii=False, indent=2)
        tech_json = json.dumps(tech,        ensure_ascii=False, indent=2)
        biz_json  = json.dumps(biz,         ensure_ascii=False, indent=2)

        if language == "ar":
            return (
                "أنت محلل أعمال وخبير تقني محترف.\n"
                "قم بتحسين مستند SRS التالي بناءً على التقييمات.\n\n"
                "قواعد صارمة جداً:\n"
                "1) أعد JSON فقط، لا تغير الهيكل أو تضف شروحات.\n"
                "2) احتفظ بنفس المفاتيح تماماً:\n"
                "   summary, metrics, sections, questions, next_steps\n"
                "3) metrics يجب أن تكون قائمة من عناصر {label, value}.\n"
                "4) sections يجب أن تكون قائمة من {title, confidence, items}.\n"
                "5) questions و next_steps يجب أن يكونوا قوائم نصوص.\n"
                "6) لا تضف أي مفاتيح جديدة.\n\n"
                f"التقييم التقني:\n{tech_json}\n\n"
                f"التقييم التجاري:\n{biz_json}\n\n"
                f"المستند الأصلي:\n{srs_json}\n\n"
                "أعد نفس الـ JSON بعد تحسين القيم فقط."
            )

        return (
            "You are a senior technical & business analyst.\n"
            "Refine the following SRS using the critiques provided.\n\n"
            "STRICT RULES:\n"
            "1) Return JSON only — do NOT change the structure or add explanations.\n"
            "2) Keep EXACT top-level keys: summary, metrics, sections, questions, next_steps\n"
            "3) metrics = list of {label, value}\n"
            "4) sections = list of {title, confidence, items}\n"
            "5) questions & next_steps = string arrays\n"
            "6) DO NOT add new keys\n\n"
            f"Technical critique:\n{tech_json}\n\n"
            f"Business critique:\n{biz_json}\n\n"
            f"Original SRS:\n{srs_json}\n\n"
            "Return the SAME JSON structure with improved values only."
        )

    def _build_summary_prompt(
        self,
        tech: Dict[str, Any],
        biz: Dict[str, Any],
        language: str,
    ) -> str:
        lang_instruction = (
            "Respond in Arabic." if language == "ar"
            else "Respond in English."
        )
        schema = (
            '{"overall_quality": "", "key_strengths": [], '
            '"key_risks": [], "priority_improvements": [], "readiness_level": ""}'
        )
        return (
            f"Generate an executive judging summary from the following critiques.\n"
            f"{lang_instruction}\n\n"
            f"Technical critique: {json.dumps(tech, ensure_ascii=False)}\n"
            f"Business critique:  {json.dumps(biz,  ensure_ascii=False)}\n\n"
            f"Return ONLY this JSON schema:\n{schema}"
        )

    # ─────────────────────────── utilities ───────────────────────────────

    @staticmethod
    def _extract_json(response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON even if wrapped in markdown/code blocks."""
        if not response:
            return None
        try:
            clean = re.sub(r"```json\s*|\s*```", "", response).strip()
            start = clean.find("{")
            end   = clean.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(clean[start:end])
        except Exception as exc:
            logger.error("JSON extraction error: %s", exc)
        return None