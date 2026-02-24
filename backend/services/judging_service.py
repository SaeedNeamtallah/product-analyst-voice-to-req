from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import SRSDraft
from backend.providers.llm.factory import LLMProviderFactory
from backend.services.srs_snapshot_cache import SRSSnapshotCache

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
        analysis_content: str = "",
        language: str = "ar",
        store_refined: bool = False,
        db: Optional[AsyncSession] = None,
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Judge SRS, refine it, generate summary, and optionally store in DB."""
        logger.info(f"Starting judgment for project {project_id} (lang={language})")

        # --- 1. Parallel Critiques ---
        tech_critique, biz_critique = await asyncio.gather(
            self._get_technical_critique(srs_content, language),
            self._get_business_critique(srs_content, language),
        )

        # --- 2. Refine SRS ---
        refined_srs = await self._refine_srs(srs_content, tech_critique, biz_critique, language)

        # --- 3. Generate Summary ---
        summary = await self._generate_summary(tech_critique, biz_critique, language)

        result = {
            "technical_critique": tech_critique,
            "business_critique": biz_critique,
            "refined_srs": refined_srs,
            "refined_analysis": analysis_content,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if store_refined and db is not None and project_id is not None:
            await self._store_refined_draft(db, project_id, language, refined_srs)

        return result

    async def _store_refined_draft(
        self,
        db: AsyncSession,
        project_id: int,
        language: str,
        refined_srs: Dict[str, Any],
    ) -> None:
        next_version_stmt = select(func.coalesce(func.max(SRSDraft.version), 0) + 1).where(
            SRSDraft.project_id == project_id
        )
        result = await db.execute(next_version_stmt)
        next_version = result.scalar_one()

        draft = SRSDraft(
            project_id=project_id,
            version=next_version,
            status="refined",
            language=language,
            content=refined_srs,
        )
        db.add(draft)
        await db.flush()
        await SRSSnapshotCache.set_from_draft(draft)

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
            max_tokens=3000
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
                "أنت كبير مهندسي البرمجيات (CTO/Architect) بخبرة في مراجعة وثائق المتطلبات.\n"
                "مهمتك: إجراء مراجعة تقنية مفصّلة لوثيقة SRS التالية.\n\n"
                "تعليمات المراجعة:\n"
                "- عند تحديد أي نقطة ضعف، اذكر عنوان القسم المعني بالضبط كما يظهر في الوثيقة.\n"
                "- حدد مستوى الخطورة لكل نقطة ضعف: Critical | High | Medium | Low.\n"
                "- لكل نقطة ضعف، قدّم إجراء إصلاحي محددًا وقابلاً للتنفيذ.\n"
                "- لا تضف متطلبات جديدة غير موجودة في الوثيقة.\n"
                "- نقاط القوة يجب أن تشير إلى أقسام بعينها.\n\n"
                "مجالات التركيز:\n"
                "المعمارية ونموذج البيانات، الأمان والمصادقة، الأداء وقابلية التوسع، "
                "نقاط التكامل، قابلية اختبار المتطلبات المحددة، المتطلبات غير الوظيفية المفقودة.\n\n"
                "أعد JSON صالح فقط بهذا الشكل:\n"
                '{"strengths": [{"section": "...", "observation": "..."}], '
                '"weaknesses": [{"section": "...", "risk": "Critical|High|Medium|Low", "issue": "...", "fix": "..."}], '
                '"risks": [{"description": "...", "mitigation": "..."}], '
                '"recommendations": ["..."]}\n\n'
                f"وثيقة SRS:\n{srs_json}"
            )
        return (
            "You are a Senior Software Architect / CTO with deep experience reviewing software requirements documents.\n"
            "Task: Perform a structured technical review of the SRS below.\n\n"
            "Review instructions:\n"
            "- When identifying a weakness, name the EXACT section title from the document.\n"
            "- Assign a risk level to each weakness: Critical | High | Medium | Low.\n"
            "- For each weakness, provide a specific, actionable remediation step.\n"
            "- Do NOT add new requirements that are absent from the document.\n"
            "- Strengths must reference specific section titles.\n\n"
            "Focus areas:\n"
            "Architecture & data model, Security & authentication, Performance & scalability, "
            "Integration points, Testability of stated requirements, Missing non-functional requirements.\n\n"
            "Return ONLY valid JSON:\n"
            '{"strengths": [{"section": "...", "observation": "..."}], '
            '"weaknesses": [{"section": "...", "risk": "Critical|High|Medium|Low", "issue": "...", "fix": "..."}], '
            '"risks": [{"description": "...", "mitigation": "..."}], '
            '"recommendations": ["..."]}\n\n'
            f"SRS document:\n{srs_json}"
        )

    def _build_business_critique_prompt(self, srs_content, language):
        srs_json = json.dumps(srs_content, ensure_ascii=False, indent=2)
        if language == "ar":
            return (
                "أنت محلل أعمال ومدير منتج بخبرة في تقييم وثائق المتطلبات.\n"
                "مهمتك: تقييم وثيقة SRS من منظور الأعمال وتوافقها مع احتياجات العميل.\n\n"
                "تعليمات التقييم:\n"
                "- اذكر عنوان القسم المعني بالضبط عند الإشارة لأي مشكلة.\n"
                "- اكشف المتطلبات الغامضة غير القابلة للقياس (مثل: سريع، جيد، عادي، مرن) وقترح بديلاً قابلاً للقياس.\n"
                "- حدد وجهات نظر المستخدمين أو السيناريوهات المفقودة.\n"
                "- قيّم وضوح قيمة الأعمال وأهداف النجاح.\n\n"
                "مجالات التركيز:\n"
                "وضوح قيمة الأعمال، مقاييس النجاح القابلة للقياس، اكتمال رحلات المستخدم، "
                "المتطلبات الغامضة، وضوح النطاق، توافق الأولويات.\n\n"
                "أعد JSON صالح فقط بهذا الشكل:\n"
                '{"strengths": [{"section": "...", "observation": "..."}], '
                '"weaknesses": [{"section": "...", "issue": "...", "suggested_fix": "..."}], '
                '"vague_requirements": [{"original": "...", "suggested_replacement": "..."}], '
                '"missing_perspectives": ["..."], '
                '"recommendations": ["..."]}\n\n'
                f"وثيقة SRS:\n{srs_json}"
            )
        return (
            "You are a Product Manager / Business Analyst with experience evaluating requirements documents.\n"
            "Task: Evaluate the SRS below for business viability and client alignment.\n\n"
            "Review instructions:\n"
            "- Reference EXACT section titles from the document when identifying issues.\n"
            "- Detect vague, unmeasurable requirements (e.g. fast, good, normal, scalable, flexible) "
            "  and suggest concrete, measurable replacements.\n"
            "- Identify missing stakeholder perspectives or user scenarios.\n"
            "- Assess clarity of business value and success criteria.\n\n"
            "Focus areas:\n"
            "Business value clarity, Measurable success metrics, User journey completeness, "
            "Vague/unmeasurable requirements, Scope clarity, Priority alignment.\n\n"
            "Return ONLY valid JSON:\n"
            '{"strengths": [{"section": "...", "observation": "..."}], '
            '"weaknesses": [{"section": "...", "issue": "...", "suggested_fix": "..."}], '
            '"vague_requirements": [{"original": "...", "suggested_replacement": "..."}], '
            '"missing_perspectives": ["..."], '
            '"recommendations": ["..."]}\n\n'
            f"SRS document:\n{srs_json}"
        )

    def _build_srs_refinement_prompt(self, srs_content, tech, biz, language):
        srs_json = json.dumps(srs_content, ensure_ascii=False, indent=2)
        tech_json = json.dumps(tech, ensure_ascii=False, indent=2)
        biz_json = json.dumps(biz, ensure_ascii=False, indent=2)

        if language == "ar":
            return (
                "أنت مهندس متطلبات أول ومهندس برمجيات متمرس.\n"
                "مهمتك: إنتاج نسخة محسّنة من وثيقة SRS بناءً على نتائج التقييمات التقنية والتجارية.\n\n"
                "قواعد التحسين الصارمة:\n"
                "1) طبّق الإصلاحات المحددة من كلا التقييمين.\n"
                "2) استبدل جميع العبارات الغامضة (سريع، جيد، عادي، قياسي، مرن) بقيم قابلة للقياس "
                "   مستمدة من سياق الوثيقة. إذا لم تتوفر قيمة قابلة للقياس، أضف سؤالاً للعميل في قسم questions "
                "   بدلاً من اختراع رقم.\n"
                "3) أعد صياغة المتطلبات بصيغة 'يجب أن يوفر النظام...' إذا لم تكن بهذه الصيغة.\n"
                "4) لا تحذف أي متطلب موجود — فقط حسّنه أو أعد صياغته.\n"
                "5) احتفظ بهيكل الـ 7 أقسام بالضبط.\n"
                "6) كل نقطة ضعف محددة في التقييمين يجب معالجتها في المخرجات.\n"
                "7) أعد JSON صالح فقط — بدون markdown أو شرح.\n\n"
                f"المستند الأصلي:\n{srs_json}\n\n"
                f"نتائج التقييم التقني:\n{tech_json}\n\n"
                f"نتائج التقييم التجاري:\n{biz_json}\n\n"
                "أعد نفس هيكل JSON مع تحسين القيم. المفاتيح الإلزامية: "
                "summary, metrics, sections, questions, next_steps"
            )

        return (
            "You are a senior requirements engineer and software architect.\n"
            "Task: Produce an improved version of the SRS by applying all critique findings.\n\n"
            "STRICT REFINEMENT RULES:\n"
            "1) Apply concrete fixes from BOTH technical and business critiques.\n"
            "2) Replace ALL vague terms (fast, good, normal, scalable, flexible, standard) with measurable "
            "   values drawn from project context. If no measurable value is available, add a client-facing "
            "   question to 'questions' instead of inventing a number.\n"
            "3) Rewrite requirements in 'The system SHALL...' format if not already.\n"
            "4) Do NOT remove any existing requirement — only improve or rephrase.\n"
            "5) Maintain the exact 7-section structure.\n"
            "6) Every weakness cited in the critiques MUST be addressed in the output.\n"
            "7) Return ONLY valid JSON — no markdown, no prose.\n\n"
            f"Original SRS:\n{srs_json}\n\n"
            f"Technical critique findings:\n{tech_json}\n\n"
            f"Business critique findings:\n{biz_json}\n\n"
            "Return the same JSON structure with improved values. Required keys: "
            "summary, metrics, sections, questions, next_steps"
        )


    def _build_summary_prompt(self, tech, biz, language):
        tech_json = json.dumps(tech, ensure_ascii=False)
        biz_json = json.dumps(biz, ensure_ascii=False)
        if language == "ar":
            return (
                "ولّد ملخصًا تنفيذيًا من نتائج التقييمات التالية.\n"
                f"التقييم التقني: {tech_json}\n"
                f"التقييم التجاري: {biz_json}\n"
                "أعد JSON صالح فقط بالمفاتيح التالية:\n"
                '{"overall_quality": "ممتاز|جيد|مقبول|ضعيف", '
                '"key_strengths": ["..."], '
                '"key_risks": ["..."], '
                '"priority_improvements": ["..."], '
                '"readiness_level": "جاهز للتطوير|يحتاج مراجعة|يحتاج إعادة عمل"}'
            )
        return (
            "Generate an executive summary from the following critique findings.\n"
            f"Technical critique: {tech_json}\n"
            f"Business critique: {biz_json}\n"
            "Return ONLY valid JSON with these keys:\n"
            '{"overall_quality": "Excellent|Good|Acceptable|Poor", '
            '"key_strengths": ["..."], '
            '"key_risks": ["..."], '
            '"priority_improvements": ["..."], '
            '"readiness_level": "Ready for Development|Needs Review|Needs Rework"}'
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

