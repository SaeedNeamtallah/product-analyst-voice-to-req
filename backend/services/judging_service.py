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
        New Feature/Refactor: Consolidated prompts, refined async handling, and structured JSON extraction.
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
        """Judge SRS, refine it, generate summary, and optionally store in DB."""
        logger.info(f"Starting judgment for project {project_id} (lang={language})")

        # --- 1. Critiques ---
        tech_critique = await self._get_technical_critique(srs_content, language)
        biz_critique = await self._get_business_critique(srs_content, language)

        # --- 2. Refine SRS ---
        refined_srs = await self._refine_srs(srs_content, tech_critique, biz_critique, language)

        # --- 3. Generate Summary ---
        summary = await self._generate_summary(tech_critique, biz_critique, language)

        result = {
            "technical_critique": tech_critique,
            "business_critique": biz_critique,
            "refined_srs": refined_srs,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat(),
        }


        return result

    # ------------------- AGENT METHODS -------------------

    async def _get_technical_critique(self, srs_content, language):
        prompt = self._build_technical_critique_prompt(srs_content, language)
        raw = await self.llm_provider.generate_text(prompt=prompt, temperature=0.3, max_tokens=3000)
        return self._extract_json(raw) or {"error": "Technical critique failed"}

    async def _get_business_critique(self, srs_content, language):
        prompt = self._build_business_critique_prompt(srs_content, language)
        raw = await self.llm_provider.generate_text(prompt=prompt, temperature=0.3, max_tokens=3000)
        return self._extract_json(raw) or {"error": "Business critique failed"}

    async def _refine_srs(self, srs_content, tech, biz, language):
        prompt = self._build_srs_refinement_prompt(srs_content, tech, biz, language)
        raw = await self.llm_provider.generate_text(
            prompt=prompt,
            temperature=0.2,
            max_tokens=4000
        )

        refined = self._extract_json(raw)   

        if not refined:
            logger.warning("Refinement failed — returning original SRS")
            return srs_content

        required_keys = ["summary", "metrics", "sections", "questions", "next_steps"]

        for key in required_keys:
            if key not in refined:
                logger.warning(f"Missing key '{key}' in refined output. Falling back.")
                return srs_content

        return refined


    async def _generate_summary(self, tech, biz, language):
        prompt = self._build_summary_prompt(tech, biz, language)
        raw = await self.llm_provider.generate_text(prompt=prompt, temperature=0.4, max_tokens=2000)
        return self._extract_json(raw) or {"status": "Summary generation failed"}

    # ------------------- PROMPT BUILDERS -------------------

    def _build_technical_critique_prompt(self, srs_content, language):
        srs_json = json.dumps(srs_content, ensure_ascii=False, indent=2)
        if language == "ar":
            return (
                f"أنت كبير مهندسي البرمجيات (CTO). قيم هذا المستند تقنياً.\n"
                f"المستند: {srs_json}\n"
                f"ركز على: المعمارية، الأداء، الأمان، والتدرج.\n"
                f"أجب بصيغة JSON فقط: {{'strengths': [], 'weaknesses': [], 'risks': [], 'recommendations': []}}"
            )
        return (
            f"You are a CTO/Senior Architect. Find technical flaws in this SRS.\n"
            f"SRS: {srs_json}\n"
            f"Focus on Architecture, Performance, Security, Scalability.\n"
            f"Return ONLY JSON: {{'strengths': [], 'weaknesses': [], 'risks': [], 'recommendations': []}}"
        )

    def _build_business_critique_prompt(self, srs_content, language):
        srs_json = json.dumps(srs_content, ensure_ascii=False, indent=2)
        if language == "ar":
            return f"أنت محلل أعمال. قيم المستند تجارياً وأخرج JSON فقط مع نقاط القوة والضعف والتوصيات.\nSRS: {srs_json}"
        return f"You are a Business Analyst. Evaluate this document and return JSON only with strengths, weaknesses, and recommendations."

    def _build_srs_refinement_prompt(self, srs_content, tech, biz, language):
        srs_json = json.dumps(srs_content, ensure_ascii=False, indent=2)
        tech_json = json.dumps(tech, ensure_ascii=False, indent=2)
        biz_json = json.dumps(biz, ensure_ascii=False, indent=2)

        if language == "ar":
            return (
                "أنت محلل أعمال وخبير تقني محترف.\n"
                "قم بتحسين مستند SRS التالي بناءً على التقييمات.\n\n"
                "قواعد صارمة جداً:\n"
                "1) لا تغيّر هيكل JSON إطلاقاً.\n"
                "2) احتفظ بنفس المفاتيح تماماً:\n"
                "   summary, metrics, sections, questions, next_steps\n"
                "3) metrics يجب أن تكون قائمة من عناصر {label, value}.\n"
                "4) sections يجب أن تكون قائمة من {title, confidence, items}.\n"
                "5) questions و next_steps يجب أن يكونوا قوائم نصوص.\n"
                "6) لا تضف أي مفاتيح جديدة.\n"
                "7) لا تشرح أي شيء خارج JSON.\n\n"
                f"التقييم التقني:\n{tech_json}\n\n"
                f"التقييم التجاري:\n{biz_json}\n\n"
                f"المستند الأصلي:\n{srs_json}\n\n"
                "أعد نفس الـ JSON بعد تحسين القيم فقط."
            )

        return (
            "You are a senior technical & business analyst.\n"
            "Refine the following SRS using the critiques.\n\n"
            "STRICT RULES:\n"
            "1) DO NOT change JSON structure.\n"
            "2) Keep EXACT keys:\n"
            "   summary, metrics, sections, questions, next_steps\n"
            "3) metrics = list of {label, value}\n"
            "4) sections = list of {title, confidence, items}\n"
            "5) questions & next_steps = string arrays\n"
            "6) DO NOT add new keys\n"
            "7) Return JSON only — no explanations\n\n"
            f"Technical critique:\n{tech_json}\n\n"
            f"Business critique:\n{biz_json}\n\n"
            f"Original SRS:\n{srs_json}\n\n"
            "Return the SAME JSON structure with improved values only."
        )


    def _build_summary_prompt(self, tech, biz, language):
        return (
            f"Generate executive summary from critiques.\n"
            f"Technical: {json.dumps(tech)}\n"
            f"Business: {json.dumps(biz)}\n"
            f"Return JSON keys: overall_quality, key_strengths, key_risks, priority_improvements, readiness_level. Language: {language}"
        )


    @staticmethod
    def _extract_json(response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON even if wrapped in markdown/codeblocks."""
        try:
            clean = re.sub(r"```json\s*|\s*```", "", response).strip()
            start, end = clean.find("{"), clean.rfind("}") + 1
            if start != -1 and end != 0:
                return json.loads(clean[start:end])
        except Exception as e:
            logger.error(f"JSON extraction error: {e}")
        return None

