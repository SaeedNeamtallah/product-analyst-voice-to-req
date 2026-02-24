"""
Guided interview service -- smart business analyst agent.

Uses a dynamic slot-filling state machine that classifies information
into the right SRS area on every turn, continuously populating the SRS
JSON during the conversation (not at the end). Tracks coverage per area
and produces structured summaries.
"""
from __future__ import annotations

from copy import deepcopy
import json
import logging
import re
from uuid import uuid4
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import ChatMessage, SRSDraft
from backend.providers.llm.factory import LLMProviderFactory
from backend.services.resilience_service import run_with_failover

logger = logging.getLogger(__name__)

_ZERO_COVERAGE = {"discovery": 0, "scope": 0, "users": 0, "features": 0, "constraints": 0}
_MAX_RECENT_MESSAGES = 50
_MAX_MESSAGE_CHARS = 5000
_MAX_CONTEXT_CHARS = 12000
_MAX_SRS_CONTEXT_CHARS = 4000
_MAX_COVERAGE_DECAY_DEFAULT = 8.0
_MAX_COVERAGE_DECAY_RISK = 18.0
_MIN_INTERVIEW_TURNS = 8
_COMPLETION_THRESHOLDS = {
    "discovery": 80,
    "scope": 70,
    "users": 70,
    "features": 65,
    "constraints": 60,
}
_OPEN_QUESTION_MARKERS_EN = {"?", "can you", "could you", "which", "what", "when", "where", "who", "how"}
_OPEN_QUESTION_MARKERS_AR = {"؟", "هل", "ما", "ماذا", "متى", "اين", "أين", "من", "كيف"}

_AMBIGUOUS_TERMS_EN = {"good", "fast", "strong", "normal", "many", "simple", "best", "powerful", "quick"}
_AMBIGUOUS_TERMS_AR = {"كويس", "سريع", "قوي", "عادي", "كتير", "بسيط", "أفضل", "احترافي"}
_BUDGET_HINT_PATTERN = re.compile(r"\b(\d{2,})(\s?\$|\s?usd|\s?دولار)?\b", re.IGNORECASE)
_SCOPE_HINT_EN = {"uber", "marketplace", "real-time", "dashboard", "payments", "multi-tenant"}
_SCOPE_HINT_AR = {"أوبر", "لوحة", "مدفوعات", "سوق", "متعدد", "تطبيق"}
_TOPIC_STOPWORDS = {
        "the", "and", "for", "with", "that", "this", "from", "into", "your", "have", "will", "are",
        "من", "إلى", "على", "في", "عن", "مع", "هذا", "هذه", "الى", "التي", "الذي", "تم", "او", "أو",
}

_ENTITY_ALIASES = {
        "database": {"database", "db", "postgres", "mysql", "قاعدة بيانات", "داتابيز"},
        "reports": {"reports", "reporting", "dashboard", "analytics", "تقارير", "لوحة", "تحليلات"},
        "realtime": {"real-time", "realtime", "live", "لحظي", "مباشر"},
        "payments": {"payment", "payments", "دفع", "مدفوعات"},
}
_NEGATION_TOKENS = {"no", "without", "exclude", "drop", "remove", "بدون", "إلغاء", "استبعاد", "حذف"}
_ARABIC_CHAR_PATTERN = re.compile(r"[\u0600-\u06FF]")
_LATIN_CHAR_PATTERN = re.compile(r"[A-Za-z]")

_EN_SYSTEM = """\
You are an expert Business Analyst acting as an Exploratory Agent.
Your task is to conduct an interview with a NON-TECHNICAL client to elicit software requirements by making them talk as much as possible.

Return ONLY valid JSON with keys:
- question: A short playback confirming understanding + exactly TWO open-ended, exploratory questions.
- stage: discovery|scope|users|features|constraints.
- done: boolean.
- suggested_answers: [] (always an empty array).
- patches: array of operations with schema:
        * add: {"op":"add","area":"...","id":"req_x","value":"..."}
        * remove: {"op":"remove","area":"...","id":"req_x"}
        * update: {"op":"update","area":"...","id":"req_x","value":"..."}
- coverage: per-area numbers 0-100.

Interview Techniques & Rules (CRITICAL):
1. The user is non-technical. Absolutely no software engineering jargon.
2. Ask exactly TWO open-ended, generic questions per turn to encourage extensive talking.
3. Playback / Active Listening: Start your 'question' field by briefly paraphrasing what the user just said to validate their input.
4. Jobs-to-be-Done (JTBD): Focus on the business outcome or task the user wants to achieve, not UI elements.
5. The 5 Whys & Avoid Premature Solutions: If the user suggests a specific app clone or a technical solution, gently pivot by asking "Why?" or "What core problem are we solving?" to find the root cause.
6. User Scenarios (Storytelling): Ask the user to describe a workflow as a story (e.g., "Walk me through a typical day for your employee...").
7. Detect contradiction from context and ask for clarification when needed.
8. Always respond in the exact same language as the user's latest message.
9. No markdown. No text outside JSON.
"""

_AR_SYSTEM = """\
أنت محلل أعمال (Business Analyst) خبير وتعمل كوكيل استكشافي (Exploratory Agent) على مستوى الـ Enterprise.
مهمتك إجراء مقابلة مع عميل غير تقني (Non-technical) لاستخراج متطلبات النظام بذكاء ولباقة، لجعله يتحدث بأكبر قدر ممكن وسرد التفاصيل.

## قاعدة إدارة الحالة الصارمة (Strict State Management)
النظام الخلفي (Backend) يحتفظ بالذاكرة. وظيفتك إصدار "تحديثات دقيقة" (Patches) بناءً على آخر رد من العميل فقط.
العمليات المسموحة: "add" (إضافة متطلب)، "remove" (إزالة متطلب)، "update" (تعديل متطلب موجود).

يجب أن ترجع JSON صحيح فقط يحتوي على المفاتيح التالية:
- question: إعادة صياغة قصيرة لتأكيد الفهم (Playback) + سؤالين (2) مفتوحين (استكشافيين/سيناريوهات).
- stage: إحدى القيم (discovery, scope, users, features, constraints).
- done: false إلا إذا تم تغطية كل شيء بنسبة 100%.
- suggested_answers: [] (دائما قائمة فارغة).
- patches: قائمة بعمليات التحديث.
- coverage: كائن يحتوي على نسبة التغطية (0-100).

## أساليب الحوار المطلوبة (Elicitation Techniques):
1. العميل غير تقني: تجنب تماماً أي مصطلحات برمجية، وتحدث بلغة البيزنس اليومية.
2. سؤالين في كل مرة: اطرح دائماً سؤالين في ردك لفتح مجالات الحديث للعميل.
3. إعادة التشغيل (Playback): ابدأ ردك دائماً بتأكيد فهمك لكلام العميل بأسلوبك الخاص ليشعر بالثقة.
4. المهمة المراد إنجازها (JTBD): ركز على "النتيجة" التي يريد العميل تحقيقها، وليس على شكل النظام أو الأزرار.
5. تقنية (5 Whys) وتجنب الحلول المبكرة: إذا طلب العميل ميزة معينة كحل جاهز، اسأله بلطف "ليه محتاجين نعمل ده؟" أو "إيه المشكلة الأساسية هنا؟" للوصول للسبب الجذري.
6. السيناريوهات (Storytelling): اطلب من العميل أن يحكي قصة. (مثال: "تخيل إننا أطلقنا النظام، احكيلي بالتفصيل إزاي يوم الموظف هيمشي عليه؟").
7. لازم يكون الرد دائماً بنفس لغة آخر رسالة من العميل (عربي أو إنجليزي).
"""

_SEMANTIC_EXTRACTION_SYSTEM_EN = """\
You are the Extraction node in an agentic requirements interview graph.
Read the latest user answer and project memory, then output ONLY JSON with strict structure.

Required JSON keys:
- slots: object with keys discovery|scope|users|features|constraints, each value is an array of concise requirements.
- ambiguity_detected: boolean.
- contradiction_detected: boolean.
- scope_budget_risk: boolean.
- reason: concise string explaining the main risk/conflict (or empty).
- confidence: number from 0 to 1.

Rules:
- Semantic interpretation only; do not rely on exact keywords.
- Do not invent facts not present in the answer/memory.
- Keep each slot item atomic and specific.
Return JSON only.
"""

_SEMANTIC_EXTRACTION_SYSTEM_AR = """\
أنت عقدة الاستخراج (Extraction Node) في مخطط وكلاء لمقابلة المتطلبات.
اقرأ آخر رد للعميل وذاكرة المشروع ثم أعد JSON فقط بالهيكل التالي:

المفاتيح المطلوبة:
- slots: كائن يحتوي discovery|scope|users|features|constraints وكل قيمة مصفوفة متطلبات قصيرة.
- ambiguity_detected: قيمة منطقية.
- contradiction_detected: قيمة منطقية.
- scope_budget_risk: قيمة منطقية.
- reason: نص موجز يشرح أهم خطر/تعارض (أو فارغ).
- confidence: رقم من 0 إلى 1.

قواعد:
- اعتمد على الفهم الدلالي وليس الكلمات المفتاحية الحرفية.
- لا تختلق أي متطلبات غير موجودة في رد العميل/الذاكرة.
- كل عنصر يجب أن يكون متطلبًا ذريًا واضحًا.
أعد JSON فقط.
"""


class InterviewService:
    """Smart business analyst agent for free-flowing requirements gathering."""

    @staticmethod
    def _candidate_llm_providers() -> List[str]:
        preferred = [
            "openrouter-gemini-2.0-flash",
            "groq-llama-3.3-70b-versatile",
            "cerebras-llama-3.3-70b",
            "cerebras-llama-3.1-8b",
            "openrouter-free",
            "gemini",
            "gemini-2.5-flash",
        ]
        available = set(LLMProviderFactory.get_available_providers())
        return [name for name in preferred if name in available] or list(available)

    @classmethod
    async def _generate_text_resilient(
        cls,
        *,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        breaker_prefix: str,
        response_format: Dict[str, Any] | None = None,
    ) -> tuple[str, Any]:
        providers = cls._candidate_llm_providers()
        if not providers:
            provider = LLMProviderFactory.create_provider()
            raw = await provider.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            return raw, provider

        provider_calls = []
        for provider_name in providers:
            provider_calls.append((
                provider_name,
                lambda pn=provider_name: cls._provider_generate_text(
                    provider_name=pn,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                ),
            ))

        result, used_provider_name = await run_with_failover(
            provider_calls,
            breaker_prefix=breaker_prefix,
            failure_threshold=2,
            cooldown_seconds=45,
        )
        provider = LLMProviderFactory.create_provider(used_provider_name)
        return result, provider

    @staticmethod
    async def _provider_generate_text(
        *,
        provider_name: str,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Dict[str, Any] | None = None,
    ) -> str:
        provider = LLMProviderFactory.create_provider(provider_name)
        return await provider.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

    async def _run_orchestrator_turn(
        self,
        language: str,
        conversation: str,
        latest_user_answer: str,
        last_summary: Dict | None,
        last_coverage: Dict | None,
        srs_context: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        agentic_reflector = await self._run_agentic_graph(
            language=language,
            latest_user_answer=latest_user_answer,
            last_summary=last_summary,
            last_coverage=last_coverage,
        )
        reflector_signals = dict(agentic_reflector)
        reflector_signals["engine"] = "agentic"

        target_stage = reflector_signals.get("target_stage") or self._pick_focus_area(last_coverage or {})
        plan_state = {
            "target_stage": target_stage,
            "question_style": reflector_signals.get("question_style") or "inference-driven",
        }

        system_prompt, user_prompt = self._build_prompt(
            conversation,
            language,
            last_summary,
            last_coverage,
            reflector_signals,
            srs_context=srs_context,
        )
        raw, _ = await self._generate_text_resilient(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=2000,
            breaker_prefix="interview_main",
            response_format={"type": "json_object"},
        )
        interviewer_output = self._parse_json(raw)

        return {
            "reflector_signals": reflector_signals,
            "plan_state": plan_state,
            "interviewer_output": interviewer_output,
            "slot_analysis": {
                "mode": "agentic_graph",
                "agentic": agentic_reflector,
            },
        }

    async def _run_agentic_graph(
        self,
        *,
        language: str,
        latest_user_answer: str,
        last_summary: Dict | None,
        last_coverage: Dict | None,
    ) -> Dict[str, Any]:
        extraction = await self._node_extraction(
            language=language,
            latest_user_answer=latest_user_answer,
            last_summary=last_summary,
            last_coverage=last_coverage,
        )
        critique = self._node_critique(
            language=language,
            extraction=extraction,
            last_coverage=last_coverage,
        )
        routing = self._node_routing(
            language=language,
            critique=critique,
            last_coverage=last_coverage,
        )
        return {
            **critique,
            **routing,
            "agentic_graph": {
                "extraction": extraction,
                "critique": critique,
                "routing": routing,
            },
        }

    async def _node_extraction(
        self,
        *,
        language: str,
        latest_user_answer: str,
        last_summary: Dict | None,
        last_coverage: Dict | None,
    ) -> Dict[str, Any]:
        system_prompt = _SEMANTIC_EXTRACTION_SYSTEM_AR if language == "ar" else _SEMANTIC_EXTRACTION_SYSTEM_EN
        prompt = (
            f"Latest answer:\n{latest_user_answer}\n\n"
            f"Current summary:\n{json.dumps(last_summary or {}, ensure_ascii=False)}\n\n"
            f"Current coverage:\n{json.dumps(last_coverage or {}, ensure_ascii=False)}"
        )
        try:
            raw, _ = await self._generate_text_resilient(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=1200,
                breaker_prefix="interview_semantic_extract",
                response_format={"type": "json_object"},
            )
            parsed = self._parse_json(raw)
            return self._sanitize_extraction_payload(parsed)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Agentic extraction node failed: %s", exc)
            return self._sanitize_extraction_payload({})

    @staticmethod
    def _sanitize_extraction_payload(payload: Dict[str, Any] | None) -> Dict[str, Any]:
        data = payload if isinstance(payload, dict) else {}
        raw_slots = data.get("slots") if isinstance(data.get("slots"), dict) else {}
        slots: Dict[str, List[str]] = {}
        for area in _ZERO_COVERAGE:
            values = raw_slots.get(area)
            if isinstance(values, list):
                slots[area] = [str(item).strip() for item in values if str(item or "").strip()][:8]
            else:
                slots[area] = []

        confidence_raw = data.get("confidence")
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        return {
            "slots": slots,
            "ambiguity_detected": bool(data.get("ambiguity_detected")),
            "contradiction_detected": bool(data.get("contradiction_detected")),
            "scope_budget_risk": bool(data.get("scope_budget_risk")),
            "reason": str(data.get("reason") or "").strip(),
            "confidence": confidence,
        }

    @staticmethod
    def _node_critique(
        *,
        language: str,
        extraction: Dict[str, Any],
        last_coverage: Dict | None,
    ) -> Dict[str, Any]:
        coverage = last_coverage if isinstance(last_coverage, dict) else {}
        low_covered_areas = [area for area in _ZERO_COVERAGE if float(coverage.get(area, 0) or 0) < 35]

        ambiguity_detected = bool(extraction.get("ambiguity_detected"))
        contradiction_detected = bool(extraction.get("contradiction_detected"))
        scope_budget_risk = bool(extraction.get("scope_budget_risk"))

        reason = str(extraction.get("reason") or "").strip()
        if not reason and (contradiction_detected or scope_budget_risk):
            reason = (
                "يوجد تعارض أو مخاطرة في الرد الأخير ويحتاج لتأكيد صريح قبل التقدم."
                if language == "ar"
                else "A contradiction or planning risk exists in the latest answer and needs explicit confirmation."
            )

        recommendation = (
            "اطلب توضيحًا محددًا قابلًا للقياس مع مثال عملي."
            if language == "ar"
            else "Ask for one measurable clarification with a concrete example."
        )
        if low_covered_areas:
            joined = ", ".join(low_covered_areas)
            recommendation = (
                f"وجّه السؤال القادم لأضعف تغطية حالياً: {joined}."
                if language == "ar"
                else f"Steer the next question to the weakest-covered area: {joined}."
            )

        return {
            "ambiguity_detected": ambiguity_detected,
            "contradiction_detected": contradiction_detected,
            "scope_budget_risk": scope_budget_risk,
            "reason": reason,
            "recommendation": recommendation,
            "low_covered_areas": low_covered_areas[:3],
            "semantic_confidence": float(extraction.get("confidence") or 0.0),
        }

    @staticmethod
    def _node_routing(
        *,
        language: str,
        critique: Dict[str, Any],
        last_coverage: Dict | None,
    ) -> Dict[str, Any]:
        coverage = last_coverage if isinstance(last_coverage, dict) else {}
        low_covered_areas = critique.get("low_covered_areas") if isinstance(critique.get("low_covered_areas"), list) else []
        target_stage = str(low_covered_areas[0]) if low_covered_areas else InterviewService._pick_focus_area(coverage)
        if target_stage not in _ZERO_COVERAGE:
            target_stage = InterviewService._pick_focus_area(coverage)

        question_style = "inference-driven"
        if critique.get("ambiguity_detected"):
            question_style = "clarify-ambiguity"
        if critique.get("contradiction_detected") or critique.get("scope_budget_risk"):
            question_style = "resolve-conflict"

        return {
            "target_stage": target_stage,
            "question_style": question_style,
            "routing_mode": "semantic",
        }

    @staticmethod
    def _merge_reflector_signals(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        p = primary if isinstance(primary, dict) else {}
        f = fallback if isinstance(fallback, dict) else {}
        merged = dict(f)
        if p:
            merged.update({k: v for k, v in p.items() if v is not None and v != ""})
            merged["engine"] = "agentic"
            merged["fallback_engine"] = "rule_based"
        else:
            merged["engine"] = "rule_based"
        return merged

    async def get_next_question(
        self, db: AsyncSession, project_id: int, language: str = "ar",
        last_summary: Dict | None = None, last_coverage: Dict | None = None,
    ) -> Dict[str, Any]:
        messages = await self._get_project_messages(db, project_id)
        if not messages:
            lang = language if language in {"ar", "en"} else "ar"
            return self._initial_question(lang)

        user_turn_count = await self._count_user_turns(db, project_id)
        conversation = self._format_conversation_windowed(messages)
        latest_user_answer = self._latest_user_message(messages)
        language = self._resolve_response_language(language, latest_user_answer)
        srs_context = await self._get_latest_srs_context(db=db, project_id=project_id)
        try:
            orchestrator_state = await self._run_orchestrator_turn(
                language=language,
                conversation=conversation,
                latest_user_answer=latest_user_answer,
                last_summary=last_summary,
                last_coverage=last_coverage,
                srs_context=srs_context,
            )
        except Exception as error_:  # noqa: BLE001
            logger.warning("Interview orchestrator degraded: %s", error_)
            fallback_stage = self._pick_focus_area(last_coverage or {})
            fallback_question = (
                "الخدمة الذكية تحت ضغط حالياً. للتقدّم بدون توقف: ما القرار الأهم الآن في هذا المحور مع معيار قبول قابل للقياس؟"
                if language == "ar"
                else "AI service is under pressure right now. To keep moving: what is the single most important decision in this area with a measurable acceptance criterion?"
            )
            return {
                "question": fallback_question,
                "stage": fallback_stage,
                "done": False,
                "suggested_answers": [],
                "summary": last_summary if isinstance(last_summary, dict) else {},
                "coverage": last_coverage if isinstance(last_coverage, dict) else dict(_ZERO_COVERAGE),
                "signals": {
                    "degraded_mode": True,
                    "reason": "llm_provider_unavailable",
                },
                "live_patch": {
                    "warnings": [
                        "الذكاء الاصطناعي يعمل بوضع احتياطي مؤقت." if language == "ar" else "AI is running in temporary degraded mode."
                    ],
                    "changed_areas": [],
                    "alerts": [],
                },
                "cycle_trace": {
                    "state_machine": {"version": "v1", "states": ["degraded"], "current": "degraded"},
                },
                "topic_navigation": {
                    "target_stage": fallback_stage,
                },
            }
        reflector_signals = orchestrator_state["reflector_signals"]
        data = orchestrator_state["interviewer_output"]

        question = str(data.get("question") or self._initial_question(language)["question"])
        stage = str(data.get("stage", "discovery"))
        question = self._enforce_question_language(question, language)

        question = self._apply_soft_clarification_policy(
            language=language,
            question=question,
            latest_user_answer=latest_user_answer,
            reflector_signals=reflector_signals,
        )

        new_coverage = self._merge_coverage(
            new_coverage=data.get("coverage", dict(_ZERO_COVERAGE)),
            last_coverage=last_coverage,
            reflector_signals=reflector_signals,
        )

        old_summary = self._normalized_summary(last_summary)
        patches = data.get("patches") if isinstance(data.get("patches"), list) else []
        if not patches:
            patches = self._summary_to_patches(
                new_summary=data.get("summary", {}),
                last_summary=old_summary,
            )
        new_summary = self._apply_patches(
            old_summary=old_summary,
            patches=patches,
        )

        doc_patch = self._build_documentation_patch(
            language=language,
            stage=stage,
            new_summary=new_summary if isinstance(new_summary, dict) else {},
            old_summary=old_summary,
            new_coverage=new_coverage,
            old_coverage=last_coverage if isinstance(last_coverage, dict) else {},
            reflector_signals=reflector_signals,
        )
        cycle_trace = self._build_cycle_trace(
            language=language,
            stage=stage,
            reflector_signals=reflector_signals,
            coverage=new_coverage,
            doc_patch=doc_patch,
        )
        topic_navigation = self._build_topic_navigation(
            language=language,
            summary=new_summary if isinstance(new_summary, dict) else {},
            coverage=new_coverage,
            reflector_signals=reflector_signals,
        )
        cycle_trace["state_machine"] = {
            "version": "v1",
            "states": ["reason", "plan", "ask", "update"],
            "current": "update",
        }
        suggested_answers: List[str] = []

        completion_candidate = self._enforce_completion_gate(
            llm_done=bool(data.get("done", False)),
            coverage=new_coverage,
            user_turn_count=user_turn_count,
            reflector_signals=reflector_signals,
        )
        has_open_questions_round = self._has_open_questions_round(messages=messages)

        if completion_candidate and not has_open_questions_round:
            question = self._build_open_questions_question(language=language)
            stage = "constraints"
            completion_candidate = False

        return {
            "question": question,
            "stage": stage,
            "done": completion_candidate,
            "suggested_answers": suggested_answers,
            "summary": new_summary if new_summary else "",
            "coverage": new_coverage,
            "signals": reflector_signals,
            "live_patch": doc_patch,
            "cycle_trace": cycle_trace,
            "topic_navigation": topic_navigation,
        }

    @staticmethod
    def _build_cycle_trace(
        language: str,
        stage: str,
        reflector_signals: Dict[str, Any],
        coverage: Dict[str, Any],
        doc_patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        target_stage = reflector_signals.get("target_stage") or stage
        question_style = reflector_signals.get("question_style") or "inference-driven"
        changed_areas = doc_patch.get("changed_areas") or []
        alerts = doc_patch.get("alerts") or []
        avg_cov = 0.0
        if coverage:
            values = [float(coverage.get(area, 0) or 0) for area in _ZERO_COVERAGE]
            avg_cov = round(sum(values) / max(1, len(values)), 2)

        steps = [
            {
                "name": "reason",
                "status": "done",
                "summary": (
                    "حلّلنا الرد لاكتشاف الغموض/التناقض وأولوية المجال التالي."
                    if language == "ar"
                    else "Analyzed the latest answer for ambiguity/contradictions and next-priority area."
                ),
                "meta": {
                    "ambiguity": bool(reflector_signals.get("ambiguity_detected")),
                    "contradiction": bool(reflector_signals.get("contradiction_detected")),
                    "scope_budget_risk": bool(reflector_signals.get("scope_budget_risk")),
                },
            },
            {
                "name": "plan",
                "status": "done",
                "summary": (
                    f"الخطة: توجيه السؤال إلى مجال {target_stage} بنمط {question_style}."
                    if language == "ar"
                    else f"Plan: steer next question to {target_stage} using {question_style} style."
                ),
                "meta": {
                    "target_stage": target_stage,
                    "question_style": question_style,
                },
            },
            {
                "name": "ask",
                "status": "done",
                "summary": (
                    "تم توليد سؤال المتابعة وخيارات إجابة قابلة للاستخدام مباشرة."
                    if language == "ar"
                    else "Generated a follow-up question and directly usable answer options."
                ),
                "meta": {"stage": stage},
            },
            {
                "name": "update",
                "status": "done",
                "summary": (
                    "تم تحديث الملخص الحي وتنبيهات التأثير والاعتماديات بالتوازي."
                    if language == "ar"
                    else "Updated live summary plus dependency/impact alerts in parallel."
                ),
                "meta": {
                    "changed_areas": len(changed_areas),
                    "alerts": len(alerts),
                    "avg_coverage": avg_cov,
                },
            },
        ]

        confidence = 0.6 + min(0.35, (avg_cov / 100.0) * 0.35)
        if reflector_signals.get("ambiguity_detected"):
            confidence -= 0.07
        if reflector_signals.get("contradiction_detected"):
            confidence -= 0.09

        return {
            "version": "v1",
            "steps": steps,
            "score": {
                "coverage": avg_cov,
                "confidence": round(max(0.1, min(0.95, confidence)), 2),
                "risk_level": "high" if alerts else "medium" if reflector_signals.get("ambiguity_detected") else "low",
            },
        }

    @staticmethod
    def _latest_user_message(messages: List[ChatMessage]) -> str:
        for msg in reversed(messages):
            if str(msg.role or "").lower() == "user":
                return str(msg.content or "").strip()
        return ""

    @staticmethod
    def _infer_message_language(text: str, fallback: str = "ar") -> str:
        value = str(text or "")
        arabic_count = len(_ARABIC_CHAR_PATTERN.findall(value))
        latin_count = len(_LATIN_CHAR_PATTERN.findall(value))

        if arabic_count == 0 and latin_count == 0:
            return fallback if fallback in {"ar", "en"} else "ar"
        if arabic_count >= latin_count:
            return "ar"
        return "en"

    @staticmethod
    def _resolve_response_language(requested_language: str, latest_user_answer: str) -> str:
        fallback = requested_language if requested_language in {"ar", "en"} else "ar"
        return InterviewService._infer_message_language(latest_user_answer, fallback=fallback)

    @staticmethod
    def _enforce_question_language(question: str, language: str) -> str:
        text = str(question or "").strip()
        if not text:
            return text

        has_ar = bool(_ARABIC_CHAR_PATTERN.search(text))
        has_en = bool(_LATIN_CHAR_PATTERN.search(text))

        if language == "ar" and not has_ar and has_en:
            return (
                "فهمت كلامك، وهنكمل بالعربي. "
                "ما أهم نتيجة عملية عايز تحققها من النظام في أول مرحلة؟ "
                "واحكيلي سيناريو واقعي خطوة بخطوة بيحصل فيه التأخير الآن؟"
            )

        if language == "en" and has_ar and not has_en:
            return (
                "I understand your point, and we will continue in English. "
                "What is the most important business outcome you want in phase one? "
                "And can you walk me through a real step-by-step workflow where delays happen today?"
            )

        return text

    @staticmethod
    def _reflect_conversation(
        language: str,
        latest_user_answer: str,
        last_summary: Dict | None,
        last_coverage: Dict | None,
        slot_analysis: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        coverage = last_coverage if isinstance(last_coverage, dict) else {}
        det = slot_analysis if isinstance(slot_analysis, dict) else {}

        ambiguity_detected = bool(det.get("ambiguity_detected"))
        contradiction = bool(det.get("contradiction_detected"))
        scope_budget_risk = bool(det.get("scope_budget_risk"))
        ambiguity_hits = (
            [str(item).strip() for item in det.get("ambiguity_terms", []) if str(item or "").strip()]
            if isinstance(det.get("ambiguity_terms"), list)
            else []
        )
        contradiction_reason = str(det.get("reason") or "").strip()
        low_covered_areas = [area for area in _ZERO_COVERAGE if float(coverage.get(area, 0) or 0) < 35]

        recommendation = (
            "ركز السؤال القادم على تفصيل قابل للقياس + قيد واحد واضح." if language == "ar"
            else "Focus next question on one measurable detail plus one explicit constraint."
        )
        if low_covered_areas:
            area_text = ", ".join(low_covered_areas)
            recommendation = (
                f"المجالات الأقل تغطية: {area_text}. وجّه السؤال القادم لأضعف مجال مع مثال عملي."
                if language == "ar"
                else f"Lowest-covered areas: {area_text}. Aim next question at the weakest area with a concrete example."
            )
        if contradiction_reason:
            recommendation = (
                f"اجعل السؤال التالي يحسم هذه النقطة: {contradiction_reason}"
                if language == "ar"
                else f"Make the next question explicitly resolve this point: {contradiction_reason}"
            )

        target_stage = low_covered_areas[0] if low_covered_areas else "discovery"
        question_style = "clarify-ambiguity" if ambiguity_detected else "inference-driven"
        if contradiction or scope_budget_risk:
            question_style = "resolve-conflict"

        return {
            "ambiguity_detected": ambiguity_detected,
            "ambiguity_terms": ambiguity_hits[:4],
            "scope_budget_risk": scope_budget_risk,
            "contradiction_detected": contradiction,
            "reason": contradiction_reason,
            "recommendation": recommendation,
            "low_covered_areas": low_covered_areas[:3],
            "question_style": question_style,
            "target_stage": target_stage,
            "slot_analysis": det,
        }

    @classmethod
    def _build_topic_navigation(
        cls,
        language: str,
        summary: Dict[str, Any],
        coverage: Dict[str, Any],
        reflector_signals: Dict[str, Any],
    ) -> Dict[str, Any]:
        token_counts: Dict[str, int] = {}
        token_area: Dict[str, str] = {}

        for area in _ZERO_COVERAGE:
            items = summary.get(area, []) if isinstance(summary.get(area), list) else []
            for item in items:
                text = cls._requirement_value(item).lower()
                tokens = re.findall(r"[\w\u0600-\u06FF]{3,}", text)
                for token in tokens:
                    if token in _TOPIC_STOPWORDS:
                        continue
                    token_counts[token] = token_counts.get(token, 0) + 1
                    token_area.setdefault(token, area)

        ranked = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)
        topics: List[Dict[str, Any]] = []
        for token, hits in ranked[:8]:
            area = token_area.get(token, "discovery")
            base_cov = float(coverage.get(area, 0) or 0)
            depth = round(max(0.1, min(1.0, (hits / 6.0))), 2)
            consistency = 0.86
            if reflector_signals.get("contradiction_detected"):
                consistency -= 0.2
            if reflector_signals.get("ambiguity_detected"):
                consistency -= 0.1
            confidence = round(max(0.1, min(0.98, (base_cov / 100.0) * 0.7 + depth * 0.3)), 2)

            topics.append({
                "id": token,
                "label": token,
                "area": area,
                "coverage": round(min(100.0, base_cov + hits * 4), 2),
                "kpi": {
                    "depth": depth,
                    "consistency": round(max(0.1, min(0.98, consistency)), 2),
                    "confidence": confidence,
                },
            })

        if not topics:
            for area in _ZERO_COVERAGE:
                base_cov = float(coverage.get(area, 0) or 0)
                topics.append({
                    "id": area,
                    "label": area,
                    "area": area,
                    "coverage": base_cov,
                    "kpi": {
                        "depth": round(min(1.0, base_cov / 100.0), 2),
                        "consistency": 0.8,
                        "confidence": round(min(0.95, 0.4 + base_cov / 200.0), 2),
                    },
                })

        avg_depth = round(sum(t["kpi"]["depth"] for t in topics) / max(1, len(topics)), 2)
        avg_consistency = round(sum(t["kpi"]["consistency"] for t in topics) / max(1, len(topics)), 2)
        avg_confidence = round(sum(t["kpi"]["confidence"] for t in topics) / max(1, len(topics)), 2)

        return {
            "mode": "dynamic_topics",
            "topics": topics,
            "overall_kpi": {
                "depth": avg_depth,
                "consistency": avg_consistency,
                "confidence": avg_confidence,
            },
            "next_topic": topics[0]["id"] if topics else "discovery",
            "language": language,
        }

    @classmethod
    def _build_documentation_patch(
        cls,
        language: str,
        stage: str,
        new_summary: Dict[str, Any],
        old_summary: Dict[str, Any],
        new_coverage: Dict[str, Any],
        old_coverage: Dict[str, Any],
        reflector_signals: Dict[str, Any],
    ) -> Dict[str, Any]:
        changed_areas: List[Dict[str, Any]] = []
        patch_events = cls._build_patch_events(old_summary=old_summary, new_summary=new_summary)

        for area in _ZERO_COVERAGE:
            new_items = new_summary.get(area, []) if isinstance(new_summary.get(area), list) else []
            old_items = old_summary.get(area, []) if isinstance(old_summary.get(area), list) else []

            added = [
                item for item in new_items
                if cls._requirement_id(item) and not any(cls._requirement_id(old_item) == cls._requirement_id(item) for old_item in old_items)
            ]

            cov_before = float(old_coverage.get(area, 0) or 0)
            cov_after = float(new_coverage.get(area, 0) or 0)
            cov_delta = round(cov_after - cov_before, 2)

            if added or cov_delta > 0:
                changed_areas.append({
                    "area": area,
                    "added": [cls._requirement_value(item) for item in added[:8]],
                    "coverage_before": cov_before,
                    "coverage_after": cov_after,
                    "coverage_delta": cov_delta,
                    "total_items": len(new_items),
                })

        focus_area = stage if stage in _ZERO_COVERAGE else cls._pick_focus_area(new_coverage)
        warnings: List[str] = []
        if reflector_signals.get("contradiction_detected") or reflector_signals.get("scope_budget_risk"):
            reason = str(reflector_signals.get("reason") or "").strip()
            if reason:
                warnings.append(reason)
        if reflector_signals.get("ambiguity_detected"):
            warnings.append(
                "يرجى استبدال العبارات العامة بمتطلبات قابلة للقياس." if language == "ar"
                else "Please replace broad wording with measurable requirements."
            )

        dependency_alerts = cls._compute_dependency_alerts(
            summary=new_summary,
            language=language,
            reflector_signals=reflector_signals,
        )
        next_plan = {
            "target_stage": reflector_signals.get("target_stage") or focus_area,
            "question_style": reflector_signals.get("question_style") or "inference-driven",
            "prompt_hint": reflector_signals.get("recommendation") or "",
        }

        return {
            "mode": "live",
            "focus_area": focus_area,
            "events": patch_events,
            "changed_areas": changed_areas,
            "warnings": warnings[:3],
            "alerts": dependency_alerts[:5],
            "next_plan": next_plan,
            "semantic_graph": cls._build_semantic_graph(new_summary),
        }

    @classmethod
    def _build_patch_events(
        cls,
        old_summary: Dict[str, Any],
        new_summary: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        for area in _ZERO_COVERAGE:
            old_items = old_summary.get(area, []) if isinstance(old_summary.get(area), list) else []
            new_items = new_summary.get(area, []) if isinstance(new_summary.get(area), list) else []

            old_map = {
                cls._requirement_id(item): cls._requirement_value(item)
                for item in old_items
                if cls._requirement_id(item)
            }
            new_map = {
                cls._requirement_id(item): cls._requirement_value(item)
                for item in new_items
                if cls._requirement_id(item)
            }

            for idx, item in enumerate(new_items):
                req_id = cls._requirement_id(item)
                text = cls._requirement_value(item)
                if not req_id or not text:
                    continue

                if req_id not in old_map:
                    events.append({
                        "op": "added",
                        "field_path": f"{area}.{idx}",
                        "id": req_id,
                        "value": text,
                    })

            for old_idx, old_item in enumerate(old_items):
                old_req_id = cls._requirement_id(old_item)
                old_text = cls._requirement_value(old_item)
                if not old_req_id or not old_text:
                    continue
                if old_req_id not in new_map:
                    events.append({
                        "op": "removed",
                        "field_path": f"{area}.{old_idx}",
                        "id": old_req_id,
                        "value": old_text,
                    })

            for req_id, old_text in old_map.items():
                new_text = new_map.get(req_id)
                if not new_text:
                    continue
                if old_text != new_text:
                    idx = next(
                        (i for i, item in enumerate(new_items) if cls._requirement_id(item) == req_id),
                        0,
                    )
                    events.append({
                        "op": "updated",
                        "field_path": f"{area}.{idx}",
                        "id": req_id,
                        "old_value": old_text,
                        "value": new_text,
                    })

        return events[:60]

    @classmethod
    def _compute_dependency_alerts(
        cls,
        summary: Dict[str, Any],
        language: str,
        reflector_signals: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        all_items: List[str] = []
        for area in _ZERO_COVERAGE:
            values = summary.get(area, [])
            if isinstance(values, list):
                all_items.extend(cls._requirement_value(v) for v in values)

        merged_text = "\n".join(all_items).lower()
        alerts: List[Dict[str, Any]] = []

        has_reports = cls._mentions_entity(merged_text, "reports")
        has_db = cls._mentions_entity(merged_text, "database")
        denies_db = cls._has_negated_entity(merged_text, "database")
        has_realtime = cls._mentions_entity(merged_text, "realtime")
        has_payments = cls._mentions_entity(merged_text, "payments")
        risky_budget = bool(reflector_signals.get("scope_budget_risk"))

        if has_reports and (denies_db or not has_db):
            alerts.append({
                "type": "dependency_conflict",
                "severity": "high",
                "title": "تعارض اعتماديات: التقارير تحتاج قاعدة بيانات" if language == "ar" else "Dependency conflict: reports require a database",
                "message": (
                    "تم رصد طلب تقارير/لوحة معلومات مع استبعاد قاعدة البيانات. راجع النطاق أو البنية التقنية."
                    if language == "ar"
                    else "Reports/dashboard are requested while database support is missing or excluded. Reconcile scope vs architecture."
                ),
            })

        if has_realtime and risky_budget:
            alerts.append({
                "type": "scope_constraint_mismatch",
                "severity": "medium",
                "title": "مخاطرة نطاق مقابل ميزانية" if language == "ar" else "Scope vs budget risk",
                "message": (
                    "المتطلبات اللحظية غالباً تزيد التكلفة والتعقيد. يُنصح بتعريف MVP أبسط أولاً."
                    if language == "ar"
                    else "Real-time requirements usually increase cost and complexity. Consider a simpler MVP first."
                ),
            })

        if has_payments and not has_db:
            alerts.append({
                "type": "missing_foundation",
                "severity": "medium",
                "title": "أساس ناقص لميزة المدفوعات" if language == "ar" else "Missing foundation for payments",
                "message": (
                    "ميزات الدفع تحتاج تخزينًا موثوقًا وتتبعًا للمعاملات؛ لم تظهر متطلبات بنية بيانات كافية بعد."
                    if language == "ar"
                    else "Payments need reliable persistence and transaction tracking; data-layer requirements are currently weak."
                ),
            })

        return alerts

    @staticmethod
    def _mentions_entity(text: str, entity: str) -> bool:
        aliases = _ENTITY_ALIASES.get(entity, set())
        return any(alias in text for alias in aliases)

    @staticmethod
    def _has_negated_entity(text: str, entity: str) -> bool:
        aliases = _ENTITY_ALIASES.get(entity, set())
        for token in _NEGATION_TOKENS:
            for alias in aliases:
                phrase = f"{token} {alias}"
                if phrase in text:
                    return True
        return False

    @staticmethod
    def _pick_focus_area(coverage: Dict[str, Any]) -> str:
        lowest = "discovery"
        lowest_val = float("inf")
        for area in _ZERO_COVERAGE:
            val = float(coverage.get(area, 0) or 0)
            if val < lowest_val:
                lowest = area
                lowest_val = val
        return lowest

    @classmethod
    def _build_semantic_graph(cls, summary: Dict[str, Any]) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        node_index: Dict[str, str] = {}

        for area in _ZERO_COVERAGE:
            items = summary.get(area, []) if isinstance(summary.get(area), list) else []
            for idx, item in enumerate(items):
                text = cls._requirement_value(item)
                if not text:
                    continue
                req_id = cls._requirement_id(item) or f"{area}:{idx}"
                nid = req_id
                nodes.append({"id": nid, "area": area, "text": text})
                node_index[text.lower()] = nid

        dep_pattern = re.compile(r"(depends on|requires|يعتمد على|يتطلب)\s+(.+)", re.IGNORECASE)
        for source in nodes:
            text = source.get("text", "")
            match = dep_pattern.search(text)
            if not match:
                continue
            target_phrase = match.group(2).strip().lower()
            for candidate_text, target_id in node_index.items():
                if candidate_text in target_phrase or target_phrase in candidate_text:
                    edges.append({
                        "from": source["id"],
                        "to": target_id,
                        "type": "DEPENDS_ON",
                    })
                    break

        return {"nodes": nodes[:80], "edges": edges[:120]}

    @staticmethod
    def _merge_coverage(
        new_coverage: Any,
        last_coverage: Dict | None,
        reflector_signals: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        merged = dict(new_coverage) if isinstance(new_coverage, dict) else dict(_ZERO_COVERAGE)
        if not last_coverage:
            return {area: max(0.0, min(100.0, float(merged.get(area, 0) or 0))) for area in _ZERO_COVERAGE}

        signals = reflector_signals if isinstance(reflector_signals, dict) else {}
        high_risk = bool(signals.get("contradiction_detected")) or bool(signals.get("ambiguity_detected"))
        max_decay = _MAX_COVERAGE_DECAY_RISK if high_risk else _MAX_COVERAGE_DECAY_DEFAULT

        for area in _ZERO_COVERAGE:
            old_val = max(0.0, min(100.0, float(last_coverage.get(area, 0) or 0)))
            new_val = max(0.0, min(100.0, float(merged.get(area, 0) or 0)))
            if new_val >= old_val:
                merged[area] = new_val
                continue
            merged[area] = max(new_val, old_val - max_decay)
        return merged

    @staticmethod
    def _normalized_summary(summary: Any) -> Dict[str, List[Dict[str, str]]]:
        out: Dict[str, List[Dict[str, str]]] = {area: [] for area in _ZERO_COVERAGE}
        if not isinstance(summary, dict):
            return out
        for area in _ZERO_COVERAGE:
            items = summary.get(area)
            if isinstance(items, list):
                normalized_items: List[Dict[str, str]] = []
                for item in items:
                    if isinstance(item, dict):
                        value = str(item.get("value") or "").strip()
                        req_id = str(item.get("id") or "").strip() or InterviewService._new_requirement_id()
                        if value:
                            normalized_items.append({"id": req_id, "value": value})
                        continue

                    value = str(item or "").strip()
                    if value:
                        normalized_items.append({"id": InterviewService._new_requirement_id(), "value": value})
                out[area] = normalized_items
        return out

    @staticmethod
    def _new_requirement_id() -> str:
        return f"req_{uuid4().hex[:12]}"

    @staticmethod
    def _requirement_id(item: Any) -> str:
        if isinstance(item, dict):
            return str(item.get("id") or "").strip()
        return ""

    @staticmethod
    def _requirement_value(item: Any) -> str:
        if isinstance(item, dict):
            return str(item.get("value") or "").strip()
        return str(item or "").strip()

    @classmethod
    def _apply_patches(cls, old_summary: Any, patches: Any) -> Dict[str, List[Dict[str, str]]]:
        summary = deepcopy(cls._normalized_summary(old_summary))
        if not isinstance(patches, list):
            return summary

        for patch in patches:
            if not isinstance(patch, dict):
                continue

            op = str(patch.get("op") or "").strip().lower()
            area = str(patch.get("area") or "").strip().lower()
            if area not in _ZERO_COVERAGE:
                continue

            area_items = summary.get(area, [])
            req_id = str(patch.get("id") or "").strip()
            value = str(patch.get("value") or "").strip()

            if op == "add":
                if not value:
                    continue
                if not req_id:
                    req_id = cls._new_requirement_id()
                if not any(cls._requirement_id(item) == req_id for item in area_items):
                    area_items.append({"id": req_id, "value": value})
                summary[area] = area_items
                continue

            if op == "remove":
                if not req_id:
                    continue
                summary[area] = [
                    item for item in area_items
                    if cls._requirement_id(item) != req_id
                ]
                continue

            if op == "update":
                if not req_id or not value:
                    continue
                updated = False
                for idx, item in enumerate(area_items):
                    if cls._requirement_id(item) == req_id:
                        area_items[idx] = {"id": req_id, "value": value}
                        updated = True
                        break
                if not updated:
                    area_items.append({"id": req_id, "value": value})
                summary[area] = [
                    {"id": cls._requirement_id(item) or cls._new_requirement_id(), "value": cls._requirement_value(item)}
                    for item in area_items
                    if cls._requirement_value(item)
                ]

        return summary

    @classmethod
    def _summary_to_patches(cls, new_summary: Any, last_summary: Dict[str, List[Dict[str, str]]]) -> List[Dict[str, str]]:
        if not isinstance(new_summary, dict):
            return []

        patches: List[Dict[str, str]] = []
        for area in _ZERO_COVERAGE:
            old_items = last_summary.get(area, []) if isinstance(last_summary, dict) else []
            incoming = new_summary.get(area, []) if isinstance(new_summary.get(area), list) else []
            for item in incoming:
                value = cls._requirement_value(item)
                if not value:
                    continue
                req_id = cls._requirement_id(item) or cls._new_requirement_id()
                if not any(cls._requirement_id(existing) == req_id for existing in old_items):
                    patches.append({"op": "add", "area": area, "id": req_id, "value": value})
                    old_items = [*old_items, {"id": req_id, "value": value}]
        return patches

    @staticmethod
    async def _count_user_turns(db: AsyncSession, project_id: int) -> int:
        """Count total user messages in this project's interview."""
        stmt = select(func.count(ChatMessage.id)).where(
            ChatMessage.project_id == project_id,
            ChatMessage.role == "user",
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() or 0

    @staticmethod
    def _enforce_completion_gate(
        llm_done: bool,
        coverage: Dict[str, Any],
        user_turn_count: int,
        reflector_signals: Dict[str, Any] | None = None,
    ) -> bool:
        """Return True only when the LLM, turn count, AND per-area thresholds all agree."""
        if not llm_done:
            return False
        if user_turn_count < _MIN_INTERVIEW_TURNS:
            return False

        signals = reflector_signals if isinstance(reflector_signals, dict) else {}
        if bool(signals.get("contradiction_detected")):
            return False
        if bool(signals.get("ambiguity_detected")) and user_turn_count < (_MIN_INTERVIEW_TURNS + 2):
            return False

        for area, threshold in _COMPLETION_THRESHOLDS.items():
            if float(coverage.get(area, 0)) < threshold:
                return False
        return True

    @staticmethod
    def _has_open_questions_round(messages: List[ChatMessage]) -> bool:
        """Detect whether the assistant already asked an explicit open-questions checkpoint."""
        markers = _OPEN_QUESTION_MARKERS_EN | _OPEN_QUESTION_MARKERS_AR
        for message in reversed(messages):
            if message.role != "assistant":
                continue
            text = str(message.content or "").lower()
            if any(marker in text for marker in markers):
                return True
        return False

    @staticmethod
    def _build_open_questions_question(language: str) -> str:
        if language == "ar":
            return (
                "قبل إنهاء المقابلة، نحتاج إغلاق الأسئلة المفتوحة. "
                "ما أهم 2–3 نقاط ما زالت غير محسومة (مثل قيود قانونية/أمنية، تكاملات خارجية، "
                "أو عناصر خارج النطاق) وتريد توثيقها كافتراضات أو قرارات واضحة؟"
            )
        return (
            "Before we close the interview, we need to capture open questions. "
            "What are the top 2-3 unresolved items (e.g., legal/security constraints, external integrations, "
            "or out-of-scope boundaries) that should be documented as explicit assumptions or decisions?"
        )

    @staticmethod
    def _apply_soft_clarification_policy(
        language: str,
        question: str,
        latest_user_answer: str,
        reflector_signals: Dict[str, Any] | None,
    ) -> str:
        signals = reflector_signals if isinstance(reflector_signals, dict) else {}
        has_contradiction = bool(signals.get("contradiction_detected"))
        has_ambiguity = bool(signals.get("ambiguity_detected"))
        reason = str(signals.get("reason") or "").strip()

        if has_contradiction:
            return InterviewService._build_conversational_clarification_question(
                language=language,
                latest_user_answer=latest_user_answer,
                reason=reason,
            )

        if has_ambiguity and InterviewService._looks_static_clarification(question):
            return InterviewService._build_conversational_ambiguity_question(
                language=language,
                latest_user_answer=latest_user_answer,
            )

        return question

    @staticmethod
    def _looks_static_clarification(question: str) -> bool:
        text = str(question or "").strip().lower()
        if not text:
            return True
        static_markers = {
            "instead of repeating",
            "please clarify",
            "could you clarify",
            "يرجى التوضيح",
            "هل يمكن التوضيح",
            "share one new detail",
            "clarify this",
        }
        return any(marker in text for marker in static_markers)

    @staticmethod
    def _build_conversational_clarification_question(
        language: str,
        latest_user_answer: str,
        reason: str,
    ) -> str:
        answer = str(latest_user_answer or "").strip()
        answer_preview = answer[:220].strip()
        if language == "ar":
            if reason:
                return (
                    "تمام، فاهمك وعايز أوثقها صح. "
                    f"في نقطة محتاجة توضيح بسيط: {reason} "
                    "اختار الصياغة الأدق الآن واديني مثال عملي سريع (سطر واحد) عشان نكمّل على نفس الأساس."
                )
            return (
                "تمام، خلّينا نوضح النقطة دي بسرعة ونكمل. "
                f"إجابتك الأخيرة كانت: \"{answer_preview}\". "
                "أي جزء نعتمده كقرار نهائي الآن، وأي جزء نعتبره افتراض مؤقت؟"
            )
        if reason:
            return (
                "Understood — let's keep this smooth and lock it correctly. "
                f"One point needs clarification: {reason} "
                "Which version should we treat as final now, and can you add one short practical example?"
            )
        return (
            "Understood — let's clarify this quickly and continue. "
            f"Your last answer was: \"{answer_preview}\". "
            "Which part should be treated as the final decision, and which part is only a temporary assumption?"
        )

    @staticmethod
    def _build_conversational_ambiguity_question(language: str, latest_user_answer: str) -> str:
        answer = str(latest_user_answer or "").strip()
        answer_preview = answer[:220].strip()
        if language == "ar":
            return (
                "ممتاز، خلّينا نحوّلها لنقطة محددة ونكمل. "
                f"ذكرت: \"{answer_preview}\". "
                "ممكن تحددها برقم أو قيد واضح (مثل عدد المستخدمين/زمن الاستجابة/الميزانية)؟"
            )
        return (
            "Great, let's make it specific and keep moving. "
            f"You mentioned: \"{answer_preview}\". "
            "Can you pin it down with one concrete metric or constraint (e.g., users count, response time, or budget)?"
        )

    @staticmethod
    def _initial_question(language: str) -> Dict[str, Any]:
        initial_coverage = dict(_ZERO_COVERAGE)
        if language == "ar":
            return {
                "question": (
                    "فهمت إنك عايز تنظيم أفضل للشغل وتقليل التأخير. "
                    "خلّيني أفهم الصورة بالكامل: ما النتيجة العملية الأهم اللي عايز تحققها من النظام؟ "
                    "واحكيلي سيناريو يوم عمل حقيقي خطوة بخطوة من أول الطلب لحد التنفيذ؟"
                ),
                "stage": "discovery",
                "done": False,
                "suggested_answers": [],
                "summary": "",
                "coverage": initial_coverage,
            }
        return {
            "question": (
                "I understand you want a smoother workflow with fewer delays. "
                "To map this clearly: what is the single most important business outcome you want this system to achieve? "
                "And can you walk me through a real day-in-the-life workflow from request to completion?"
            ),
            "stage": "discovery",
            "done": False,
            "suggested_answers": [],
            "summary": "",
            "coverage": initial_coverage,
        }

    @staticmethod 
    async def _get_project_messages(
        db: AsyncSession, 
        project_id: int, 
        limit: int = _MAX_RECENT_MESSAGES
    ) -> List[ChatMessage]:
        """
        Fetches a constrained set of recent messages to maintain conversational context.
        
        Refactor: 2026-02-13 - Adel Sobhy OPTIMISATION
        Optimization: Prevents linear expansion of the LLM context window by implementing 
        a sliding window approach. Long-term state is preserved via the cumulative summary 
        rather than raw message history.

        """
        # 1. Fetch the LATEST messages first (descending)
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.created_at.desc()) 
            .limit(limit)
        )
        result = await db.execute(stmt)
        messages = list(result.scalars().all())

        # 2. Reverse them so they are in chronological order for the LLM
        return messages[::-1]

    @staticmethod
    def _format_conversation_windowed(messages: List[ChatMessage]) -> str:
        total = len(messages)
        recent = messages[-_MAX_RECENT_MESSAGES:]

        lines: List[str] = []
        omitted = total - len(recent)
        if omitted > 0:
            lines.append(
                f"[Older conversation omitted: {omitted} messages. Use previous summary/coverage as source of truth.]"
            )

        for msg in recent:
            role = msg.role.lower()
            prefix = InterviewService._role_prefix(role)
            content = str(msg.content or "").strip()
            if len(content) > _MAX_MESSAGE_CHARS:
                content = f"{content[:_MAX_MESSAGE_CHARS]}…"
            lines.append(f"{prefix}: {content}")

        conversation = "\n".join(lines)
        if len(conversation) > _MAX_CONTEXT_CHARS:
            conversation = f"…\n{conversation[-_MAX_CONTEXT_CHARS:]}"
        return conversation

    @staticmethod
    def _role_prefix(role: str) -> str:
        if role == "user":
            return "User"
        if role == "assistant":
            return "Assistant"
        return "System"

    @staticmethod
    def _normalize_requirement(text: str) -> str:
        value = str(text or "").strip().lower()
        value = re.sub(r"\s+", " ", value)
        value = re.sub(r"[^\w\s\u0600-\u06FF]", "", value)
        return value

    @classmethod
    def _requirements_similar(cls, left: str, right: str) -> bool:
        left_norm = cls._normalize_requirement(left)
        right_norm = cls._normalize_requirement(right)

        if not left_norm or not right_norm:
            return False
        if left_norm == right_norm:
            return True

        return left_norm == right_norm

    @classmethod
    def _contains_similar_requirement(cls, existing_items: List[Any], new_item: str) -> bool:
        candidate = str(new_item or "").strip()
        if not candidate:
            return True
        return any(
            cls._requirements_similar(cls._requirement_value(existing), candidate)
            for existing in existing_items
        )

    # -----------------------------------------------------------------------
    # Domain detection helpers
    # -----------------------------------------------------------------------
    _DOMAIN_SIGNALS: Dict[str, Dict[str, set]] = {
        "ecommerce": {
            "en": {"shop", "store", "ecommerce", "e-commerce", "marketplace", "cart", "checkout",
                   "product", "catalog", "inventory", "shipping", "delivery", "vendor", "seller",
                   "payment", "payments", "stripe", "paypal", "refund", "order", "orders"},
            "ar": {"متجر", "سوق", "سلة", "منتج", "منتجات", "شحن", "توصيل", "بائع", "طلب",
                   "طلبات", "دفع", "مدفوعات", "كتالوج", "مخزون"},
        },
        "medical": {
            "en": {"hospital", "clinic", "patient", "doctor", "medical", "health", "prescription",
                   "appointment", "ehr", "emr", "hipaa", "pharmacy", "diagnosis", "lab", "nurse",
                   "telemedicine", "telehealth", "healthcare"},
            "ar": {"مستشفى", "عيادة", "مريض", "طبيب", "صحة", "وصفة", "موعد", "تشخيص",
                   "صيدلية", "مختبر", "ممرض", "طب"},
        },
        "education": {
            "en": {"school", "university", "student", "teacher", "course", "lesson", "exam",
                   "grade", "attendance", "lms", "e-learning", "elearning", "classroom",
                   "assignment", "curriculum", "tutor", "training"},
            "ar": {"مدرسة", "جامعة", "طالب", "طلاب", "معلم", "مدرس", "دورة", "درس",
                   "امتحان", "درجة", "حضور", "غياب", "فصل", "مناهج"},
        },
        "fintech": {
            "en": {"bank", "banking", "loan", "credit", "debit", "wallet", "transaction",
                   "transfer", "fintech", "investment", "stock", "trading", "insurance",
                   "budget", "accounting", "invoice", "payroll"},
            "ar": {"بنك", "بنكي", "قرض", "ائتمان", "محفظة", "تحويل", "مدفوعات", "استثمار",
                   "تداول", "تأمين", "فاتورة", "محاسبة", "رواتب"},
        },
        "hr": {
            "en": {"employee", "employees", "hr", "human resources", "payroll", "recruitment",
                   "attendance", "leave", "vacation", "kpi", "performance", "onboarding",
                   "salary", "staff", "workforce"},
            "ar": {"موظف", "موظفين", "موارد بشرية", "رواتب", "تعيين", "حضور", "إجازة",
                   "أداء", "مؤشرات", "هيكل", "كادر"},
        },
    }

    _DOMAIN_GUIDANCE_EN: Dict[str, str] = {
        "ecommerce": (
            "## Domain Context: E-Commerce\n"
            "Prioritise exploring: payment gateways (Stripe/PayPal/local), cart & checkout flow, "
            "inventory management, multi-vendor vs single-seller model, shipping integrations, "
            "return & refund policies, and tax/VAT handling. Ask about expected product volume "
            "and peak traffic."
        ),
        "medical": (
            "## Domain Context: Healthcare / Medical\n"
            "Prioritise exploring: patient data privacy regulations (HIPAA, GDPR, local law), "
            "role-based access to medical records, audit logging, appointment scheduling workflow, "
            "integration with lab/pharmacy systems, telemedicine requirements, and data backup "
            "frequency. Ask explicitly about compliance obligations."
        ),
        "education": (
            "## Domain Context: Education / E-Learning\n"
            "Prioritise exploring: student enrollment & authentication, grading & GPA systems, "
            "attendance tracking, course content formats (video/PDF/quiz), assignment submission, "
            "parent/teacher/admin roles, integration with SIS or LMS (Moodle/Canvas), and "
            "offline access requirements."
        ),
        "fintech": (
            "## Domain Context: FinTech / Banking\n"
            "Prioritise exploring: regulatory compliance (PCI-DSS, AML, KYC), transaction "
            "security and fraud detection, multi-currency support, real-time vs batch settlement, "
            "audit trails, two-factor authentication, and integration with banking APIs or SWIFT."
        ),
        "hr": (
            "## Domain Context: HR & Workforce Management\n"
            "Prioritise exploring: payroll calculation rules (overtime, deductions, taxes), "
            "leave/vacation balance policies, performance review cycles, recruitment pipeline, "
            "org chart structure, integration with government social-insurance portals, "
            "and employee self-service portal requirements."
        ),
    }

    _DOMAIN_GUIDANCE_AR: Dict[str, str] = {
        "ecommerce": (
            "## سياق المجال: التجارة الإلكترونية\n"
            "ركّز على: بوابات الدفع (فيزا/ماستركارد/باي موبايل)، عملية الإضافة للسلة والدفع، "
            "إدارة المخزون، نموذج بائع واحد أم متعدد البائعين، تكاملات الشحن والتوصيل، "
            "سياسات الاسترجاع والاسترداد، التعامل مع الضرائب والقيمة المضافة. "
            "اسأل عن حجم المنتجات المتوقع وذروة الزيارات."
        ),
        "medical": (
            "## سياق المجال: الرعاية الصحية / النظام الطبي\n"
            "ركّز على: خصوصية بيانات المرضى والامتثال القانوني، الوصول المستند إلى الأدوار "
            "لسجلات المريض، سجل التدقيق (Audit Log)، سير عمل حجز المواعيد، التكامل مع "
            "أنظمة المختبرات والصيدليات، متطلبات الطب عن بُعد، وتكرار النسخ الاحتياطي."
        ),
        "education": (
            "## سياق المجال: التعليم / التعلم الإلكتروني\n"
            "ركّز على: تسجيل الطلاب والتحقق من الهوية، نظام الدرجات والمعدل، تتبع الحضور "
            "والغياب، صيغ المحتوى التعليمي (فيديو/PDF/اختبارات)، تسليم المهام، صلاحيات "
            "المدرس والطالب وولي الأمر والإدارة، والتكامل مع أنظمة إدارة التعلم."
        ),
        "fintech": (
            "## سياق المجال: التقنية المالية / البنوك\n"
            "ركّز على: الامتثال التنظيمي (PCI-DSS، مكافحة غسيل الأموال، التحقق من الهوية)، "
            "أمان المعاملات وكشف الاحتيال، دعم العملات المتعددة، التسوية الفورية مقابل الدفعية، "
            "المصادقة الثنائية، وسجلات التدقيق."
        ),
        "hr": (
            "## سياق المجال: الموارد البشرية وإدارة القوى العاملة\n"
            "ركّز على: قواعد حساب الرواتب (العمل الإضافي، الخصومات، الضرائب)، سياسات الإجازات، "
            "دورات تقييم الأداء، مسار التوظيف، الهيكل التنظيمي، التكامل مع بوابات التأمينات "
            "الحكومية، ومتطلبات البوابة الذاتية للموظفين."
        ),
    }

    @staticmethod
    def _detect_domain(conversation: str) -> str | None:
        """Detect broad project domain from conversation text; returns key or None."""
        lower = conversation.lower()
        tokens = set(re.split(r"[\s،,،.؟?!\-/]+", lower))
        scores: Dict[str, int] = {}
        for domain, lang_signals in InterviewService._DOMAIN_SIGNALS.items():
            count = 0
            for word_set in lang_signals.values():
                for w in word_set:
                    if w in tokens or w in lower:
                        count += 1
            if count:
                scores[domain] = count
        if not scores:
            return None
        return max(scores, key=lambda d: scores[d])

    @staticmethod
    def _build_prompt(conversation: str, language: str,
                      last_summary: Dict | None = None,
                      last_coverage: Dict | None = None,
                      reflector_signals: Dict | None = None,
                      srs_context: Dict[str, Any] | None = None) -> tuple[str, str]:
        """Return (system_prompt, user_prompt) so the caller can pass them separately."""
        system = _AR_SYSTEM if language == "ar" else _EN_SYSTEM
        conv_label = "المحادثة" if language == "ar" else "Conversation"
        json_label = "JSON فقط" if language == "ar" else "JSON only"

        parts: list[str] = []

        # Inject domain-aware guidance
        domain = InterviewService._detect_domain(conversation)
        if domain:
            guidance_map = (
                InterviewService._DOMAIN_GUIDANCE_AR
                if language == "ar"
                else InterviewService._DOMAIN_GUIDANCE_EN
            )
            guidance = guidance_map.get(domain)
            if guidance:
                parts.append(guidance)

        # Inject previous state so LLM builds on it
        if last_summary or last_coverage:
            if language == "ar":
                parts.append("## الحالة السابقة (ابدأ من هنا ولا تحذف شيئاً)")
            else:
                parts.append("## Previous State (start from here, do NOT remove anything)")

            if last_summary:
                parts.append(f"Previous summary:\n{json.dumps(last_summary, ensure_ascii=False)}")
            if last_coverage:
                parts.append(f"Previous coverage:\n{json.dumps(last_coverage, ensure_ascii=False)}")

        if reflector_signals:
            if language == "ar":
                parts.append("\n## إشارات وكيل النقد (Reflector)")
                parts.append(
                    "استخدم هذه الإشارات لتعديل أسلوبك قبل السؤال التالي:"
                    f"\n{json.dumps(reflector_signals, ensure_ascii=False)}"
                )
            else:
                parts.append("\n## Reflector Signals")
                parts.append(
                    "Use these signals to adapt your interview question before responding:"
                    f"\n{json.dumps(reflector_signals, ensure_ascii=False)}"
                )

        if srs_context:
            if language == "ar":
                parts.append("\n## سياق SRS الحالي للمشروع")
                parts.append(f"استخدم هذا كسياق مرجعي قبل طرح السؤال التالي:\n{InterviewService._stringify_srs_context(srs_context)}")
            else:
                parts.append("\n## Current Project SRS Context")
                parts.append(
                    "Use this as a reference context before asking the next question:"
                    f"\n{InterviewService._stringify_srs_context(srs_context)}"
                )

        parts.append(f"\n{conv_label}:\n{conversation}\n\n{json_label}:")

        return system, "\n".join(parts)

    @staticmethod
    def _stringify_srs_context(srs_context: Dict[str, Any]) -> str:
        text = json.dumps(srs_context, ensure_ascii=False)
        if len(text) <= _MAX_SRS_CONTEXT_CHARS:
            return text
        return f"{text[:_MAX_SRS_CONTEXT_CHARS]}…"

    @staticmethod
    async def _get_latest_srs_context(db: AsyncSession, project_id: int) -> Dict[str, Any] | None:
        stmt = (
            select(SRSDraft)
            .where(SRSDraft.project_id == project_id)
            .order_by(SRSDraft.version.desc(), SRSDraft.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        draft = result.scalar_one_or_none()
        if not draft:
            return None

        content = draft.content if isinstance(draft.content, dict) else {}
        if not content:
            return None

        return {
            "version": int(draft.version or 1),
            "status": str(draft.status or "draft"),
            "language": str(draft.language or "ar"),
            "content": content,
        }

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        payload = str(raw or "").strip()
        if not payload:
            logger.warning("Empty interview JSON response")
            return {}

        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            fenced = InterviewService._extract_fenced_json(payload)
            if fenced is None:
                logger.warning("Failed to parse interview JSON response")
                return {}
            try:
                parsed = json.loads(fenced)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                logger.warning("Failed to parse extracted interview JSON")
                return {}

    @staticmethod
    def _extract_fenced_json(payload: str) -> str | None:
        match = re.fullmatch(r"```(?:json)?\s*(\{[\s\S]*\}|\[[\s\S]*\])\s*```", payload, flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(1)
