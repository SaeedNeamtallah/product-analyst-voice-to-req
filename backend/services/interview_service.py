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
_MAX_USER_MESSAGE_CHARS = 3000  # Truncate user messages longer than this before sending to LLM
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
You are an expert Business Analyst acting as a fast, conversational Exploratory Agent.
Your task is to conduct an interview with a NON-TECHNICAL client to elicit software requirements.

Return ONLY valid JSON with keys:
    "question": "your response to the user",
    "stage": "discovery|scope|users|features|constraints",
    "done": boolean (true if the user has provided enough details to cover the majority of the system)

Interview Techniques & Rules (CRITICAL):
1. The user is non-technical. Absolutely no software engineering jargon.
2. If the user provides a massive, detailed message (like a full list of requirements or a business plan), acknowledge it quickly: e.g., "This is excellent detail, I am saving this right now." and ask ONE follow up question. You DO NOT need to extract the data yourself, a background agent will do it.
3. Playback / Active Listening: Start your 'question' field by briefly paraphrasing what the user just said to validate their input.
4. Jobs-to-be-Done (JTBD): Focus on the business outcome or task the user wants to achieve, not UI elements.
5. The 5 Whys & Avoid Premature Solutions: If the user suggests a specific app clone or a technical solution, gently pivot by asking "Why?".
6. Always respond in the exact same language as the user's latest message.
7. No markdown. No text outside JSON.
8. Anti-Hallucination: Do not invent, assume, or suggest features, constraints, or numbers that the user has not explicitly mentioned. Base your questions strictly on the provided context.
"""

_AR_SYSTEM = """\
أنت محلل أعمال خبير وتعمل كوكيل استكشافي سريع (Fast Conversational Agent).
مهمتك إجراء مقابلة مع عميل غير تقني لاستخراج متطلبات النظام.

يجب أن ترجع JSON صحيح فقط يحتوي على المفاتيح التالية:
    "question": "نص سؤالك أو ردك",
    "stage": "إحدى المراحل discovery|scope|users|features|constraints",
    "done": قيمة منطقية true في حال قدم العميل تفاصيل تكفي لتغطية النظام

أساليب الحوار المطلوبة (CRITICAL):
1. العميل غير تقني: تجنب تماماً أي مصطلحات برمجية، وتحدث بلغة البيزنس اليومية.
2. التعامل مع السرد الكثيف: إذا قام العميل بتقديم رسالة طويلة جداً أو دراسة جدوى، قم بالرد السريع لشكر العميل وطمأنته أنك تسجلها الآن (مثلاً: "هذه تفاصيل ممتازة جداً، جاري حفظها بالكامل في مستند المتطلبات.") ثم اطرح سؤالاً واحداً فقط للمتابعة. لست بحاجة لاستخراج البيانات بنفسك، هناك وكيل في الخلفية يقوم بذلك.
3. إعادة التشغيل (Playback): ابدأ ردك دائماً بتأكيد فهمك لكلام العميل بأسلوبك الخاص ليشعر بالثقة.
4. المهمة المراد إنجازها (JTBD): ركز على "النتيجة" التي يريد العميل تحقيقها، وليس على شكل النظام أو الأزرار.
5. تقنية (5 Whys): إذا طلب العميل ميزة معينة كحل جاهز، اسأله بلطف "ليه محتاجين نعمل ده؟" للوصول للسبب الجذري.
6. لازم يكون الرد دائماً بنفس لغة آخر رسالة من العميل (عربي أو إنجليزي).
7. منع التأليف (Anti-Hallucination): لا تقم باختراع أو افتراض أو اقتراح ميزات أو أرقام لم يذكرها العميل. 
8. إرجاع JSON فقط.
"""


_SEMANTIC_EXTRACTION_SYSTEM_EN = """\
You are the Extraction node in an agentic requirements interview graph.
Your role is to act as an \"Information Sponge\". Read the latest user answer and project memory, then output ONLY JSON with strict structure.

Required JSON keys:
- slots: object with keys discovery|scope|users|features|constraints, each value is an array of concise requirements.
- ambiguity_detected: boolean.
- contradiction_detected: boolean.
- scope_budget_risk: boolean.
- reason: concise string explaining the main risk/conflict (or empty).
- confidence: number from 0 to 1.

Omnivorous Extraction Rules (CRITICAL):
1. Absolute Assimilation: Capture ANY business or technical requirement mentioned by the user and classify it into the correct slot, EVEN IF it does not directly answer your previous question. Do not ignore unprompted details.
2. Bulk Data Handling: If the user provides a massive dump of information, stories, or examples, extract every single feature, constraint, or user role embedded in the text as a separate item in the slots.
3. Extract implicit requirements from the user's narrative, not just direct answers.
4. Semantic interpretation only; do not rely on exact keywords.
5. Anti-Hallucination: While extracting implicit needs, NEVER invent net-new features or assumptions. Every extracted slot must have a direct basis in the user's narrative.
6. Return JSON only.
"""


_SEMANTIC_EXTRACTION_SYSTEM_AR = """\
أنت عقدة الاستخراج (Extraction Node) في مخطط وكلاء لمقابلة المتطلبات.
مهمتك هي العمل كـ \"إسفنجة معلومات\". اقرأ آخر رد للعميل وذاكرة المشروع ثم أعد JSON فقط بالهيكل التالي.

المفاتيح المطلوبة:
- slots: كائن يحتوي discovery|scope|users|features|constraints وكل قيمة مصفوفة متطلبات قصيرة.
- ambiguity_detected: قيمة منطقية.
- contradiction_detected: قيمة منطقية.
- scope_budget_risk: قيمة منطقية.
- reason: نص موجز يشرح أهم خطر/تعارض (أو فارغ).
- confidence: رقم من 0 إلى 1.

قواعد الاستخراج الشامل (CRITICAL RULES):
1. الاستيعاب المطلق (Omnivorous Extraction): التقط **أي** معلومة تقنية أو تجارية يذكرها العميل وصنفها في الـ slot المناسب، حتى لو كانت إجابته لا علاقة لها بالسؤال المطروح. لا تتجاهل أي تفصيلة.
2. التعامل مع السرد الكثيف (Bulk Data): إذا قام العميل بذكر تفاصيل كثيرة جداً مرة واحدة (رغي/أمثلة/سيناريوهات)، استخرج كل ميزة، أو قيد، أو دور مستخدم ذكر في السرد وضعه كعنصر مستقل في الـ slots.
3. التحديث المستقل: لا تعتمد فقط على الرد المباشر على السؤال، ابحث عن المتطلبات الضمنية (Implicit Requirements) داخل كلام العميل.
4. اعتمد على الفهم الدلالي وليس الكلمات المفتاحية الحرفية.
5. منع التأليف (Anti-Hallucination): أثناء استخراج المتطلبات الضمنية، يُمنع تماماً اختراع ميزات أو افتراضات جديدة. يجب أن يكون لكل متطلب مستخرج أساس مباشر في سرد العميل.
6. أعد JSON فقط.
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
            max_tokens=4000,  # Increased to reduce truncation risk
            breaker_prefix="interview_main",
            response_format={"type": "json_object"},
        )
        interviewer_output = self._parse_json(raw)
        interviewer_output = self._normalize_interviewer_output(
            payload=interviewer_output,
            language=language,
            target_stage=target_stage,
            fallback_coverage=last_coverage,
        )

        return {
            "reflector_signals": reflector_signals,
            "plan_state": plan_state,
            "interviewer_output": interviewer_output,
            "slot_analysis": {
                "mode": "agentic_graph",
                "agentic": agentic_reflector,
            },
        }

    @staticmethod
    def _normalize_interviewer_output(
        payload: Dict[str, Any] | None,
        language: str,
        target_stage: str,
        fallback_coverage: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        data = payload if isinstance(payload, dict) else {}
        question = str(data.get("question") or "").strip()
        if not question:
            question = (
                "شكراً على مشاركتك! هل يمكنك إخبارنا بمزيد من التفاصيل عن المشروع؟"
                if language == "ar"
                else "Thank you for sharing! Could you tell us more details about what you'd like to build?"
            )
        stage = str(data.get("stage") or target_stage or "discovery").strip().lower()
        if stage not in _ZERO_COVERAGE:
            stage = target_stage if target_stage in _ZERO_COVERAGE else "discovery"

        raw_coverage = data.get("coverage") if isinstance(data.get("coverage"), dict) else {}
        base_coverage = fallback_coverage if isinstance(fallback_coverage, dict) else {}
        merged_coverage: Dict[str, float] = {}
        for area in _ZERO_COVERAGE:
            source_value = raw_coverage.get(area, base_coverage.get(area, 0))
            try:
                numeric = float(source_value)
            except (TypeError, ValueError):
                numeric = float(base_coverage.get(area, 0) or 0)
            merged_coverage[area] = max(0.0, min(100.0, numeric))

        patches = data.get("patches") if isinstance(data.get("patches"), list) else []
        suggested_answers = data.get("suggested_answers") if isinstance(data.get("suggested_answers"), list) else []

        return {
            "question": question,
            "stage": stage,
            "done": bool(data.get("done", False)),
            "suggested_answers": suggested_answers,
            "patches": patches,
            "coverage": merged_coverage,
            "summary": data.get("summary", {}),
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

    async def get_chat_response(
        self, db: AsyncSession, project_id: int, language: str = "ar",
        last_summary: Dict | None = None, last_coverage: Dict | None = None,
        aim_for_100: bool = False
    ) -> Dict[str, Any]:
        messages = await self._get_project_messages(db, project_id)
        if not messages:
            lang = language if language in {"ar", "en"} else "ar"
            return self._initial_question(lang)

        conversation = await self._format_conversation_windowed(messages)
        latest_user_answer = self._latest_user_message(messages)
        language = self._resolve_response_language(language, latest_user_answer)

        if self._is_duplicate_message(messages):
            dup_msg = (
                "يبدو أنك أرسلت نفس الرسالة مرة أخرى. هل هناك شيء محدد تريد إضافته أو توضيحه؟"
                if language == "ar"
                else "It looks like you sent the same message again. Is there something specific you'd like to add or clarify?"
            )
            return {"question": dup_msg, "stage": "discovery", "done": False}

        if len(latest_user_answer) > _MAX_USER_MESSAGE_CHARS:
            logger.warning(
                "User answer too long (%d chars) — truncating to %d for LLM safety.",
                len(latest_user_answer), _MAX_USER_MESSAGE_CHARS,
            )
            latest_user_answer = latest_user_answer[:_MAX_USER_MESSAGE_CHARS] + "… [تم اقتطاع الرسالة لأسباب تقنية]"

        srs_context = await self._get_latest_srs_context(db=db, project_id=project_id)
        
        system_prompt = _AR_SYSTEM if language == "ar" else _EN_SYSTEM
        user_prompt = f"Target language: {language}\n\n"
        if srs_context:
            user_prompt += f"Existing SRS Context:\n{json.dumps(srs_context, ensure_ascii=False)}\n\n"
        if aim_for_100:
            if language == "ar":
                user_prompt += "CRITICAL INSTRUCTION: العميل يريد الاستمرار في المقابلة للوصول إلى تفاصيل بنسبة 100% في كافة الجوانب. لا تقم بإرجاع done=true إلا إذا استنفدت كل الأسئلة الممكنة حرفياً.\n\n"
            else:
                user_prompt += "CRITICAL INSTRUCTION: The client wants to continue the interview to reach 100% coverage in ALL areas. Do NOT output done=true unless you have absolutely exhausted every possible detail and edge case.\n\n"
        user_prompt += f"Conversation history:\n{conversation}\n\nClient's latest reply: {latest_user_answer}"

        try:
            raw, _ = await self._generate_text_resilient(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=600,
                breaker_prefix="interview_chatter",
                response_format={"type": "json_object"},
            )
            data = self._parse_json(raw)
        except Exception as error_:
            logger.warning("Chatter agent degraded: %s", error_, exc_info=True)
            data = {}

        question = str(data.get("question") or self._initial_question(language)["question"])
        stage = str(data.get("stage") or self._pick_focus_area(last_coverage or {}))
        done = bool(data.get("done", False))

        if aim_for_100 and done:
            current_cov = last_coverage or {}
            for area in _COMPLETION_THRESHOLDS.keys():
                if float(current_cov.get(area, 0)) < 100.0:
                    done = False
                    break

        question = self._enforce_question_language(question, language)

        return {
            "question": question,
            "stage": stage,
            "done": done,
            "suggested_answers": [],
            "signals": {"engine": "chatter", "fast_mode": True},
            "live_patch": {},
            "cycle_trace": {},
            "topic_navigation": {"target_stage": stage},
        }

    async def extract_background_patches(
        self, project_id: int, language: str, session_factory: Any
    ) -> None:
        """Asynchronous background task to extract semantic patches using LivePatchService."""
        from backend.services.live_patch_service import LivePatchService
        from backend.database.models import SRSDraft, Project
        from sqlalchemy import select
        
        async with session_factory() as db:
            try:
                # 1. Lock project to safely update SRSDraft
                stmt_lock = select(Project).where(Project.id == project_id).with_for_update()
                locked_project = await db.scalar(stmt_lock)
                if not locked_project:
                    return

                messages = await self._get_project_messages(db, project_id)
                if not messages:
                    return

                stmt_draft = select(SRSDraft).where(SRSDraft.project_id == project_id).order_by(SRSDraft.version.desc()).limit(1).with_for_update()
                latest_draft = await db.scalar(stmt_draft)

                draft_content = latest_draft.content if latest_draft and isinstance(latest_draft.content, dict) else {}
                old_summary = draft_content.get("summary", {}) if draft_content else {}
                old_coverage = draft_content.get("coverage", {}) if draft_content else {}

                # 2. Extract using the robust, decoupled LivePatchService!
                result = await LivePatchService.build_from_messages(
                    language=language,
                    messages=messages,
                    last_summary=old_summary,
                    last_coverage=old_coverage,
                )

                # 3. Save new state
                new_content = {
                    "summary": result.get("summary", old_summary),
                    "coverage": result.get("coverage", old_coverage),
                }

                if latest_draft:
                    latest_draft.content = new_content
                    latest_draft.version += 1
                else:
                    new_draft = SRSDraft(project_id=project_id, content=new_content, version=1)
                    db.add(new_draft)

                await db.commit()
                logger.info(f"Background extraction completed for project {project_id}")

            except Exception as e:
                await db.rollback()
                logger.error(f"Background extraction failed for project {project_id}: {e}")
    # Legacy variables unused by Chatter but referenced by other methods
    # We leave _run_orchestrator_turn and related functions here in case they are used elsewhere

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
    def _is_duplicate_message(messages: List[ChatMessage]) -> bool:
        """Return True if the last two user messages are identical (after normalization).
        Prevents re-processing when a user accidentally sends the same message multiple times.
        """
        user_msgs = [m for m in messages if m.role == "user"]
        if len(user_msgs) < 2:
            return False
        def _norm(text: str) -> str:
            return re.sub(r"\s+", " ", str(text or "").strip().lower())
        return _norm(user_msgs[-1].content) == _norm(user_msgs[-2].content)

    @staticmethod
    def _enforce_question_language(question: str, language: str) -> str:
        """Ensure the question is in the correct language. If a mismatch is detected,
        prepend a translated version so the user always sees their own language."""
        text = str(question or "").strip()
        if not text:
            return text

        arabic_chars = len(_ARABIC_CHAR_PATTERN.findall(text))
        latin_chars = len(_LATIN_CHAR_PATTERN.findall(text))
        total = arabic_chars + latin_chars
        if total == 0:
            return text

        arabic_ratio = arabic_chars / total

        if language == "ar" and arabic_ratio < 0.4:
            # LLM returned English in an Arabic conversation
            logger.warning("Language mismatch detected: expected AR, got mostly EN. Prepending AR note.")
            return (
                "(ملاحظة: تم اكتشاف رد بلغة مختلفة — يرجى الإجابة بالعربية)\n"
                + text
            )
        if language == "en" and arabic_ratio > 0.6:
            # LLM returned Arabic in an English conversation
            logger.warning("Language mismatch detected: expected EN, got mostly AR. Prepending EN note.")
            return (
                "(Note: Response was detected in a different language — please reply in English)\n"
                + text
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
        # Use specific checkpoint phrases instead of generic question markers
        # to avoid false positives from normal interview questions.
        checkpoint_phrases_en = {
            "before we close the interview",
            "capture open questions",
            "unresolved items",
            "documented as explicit assumptions",
            "out-of-scope boundaries",
        }
        checkpoint_phrases_ar = {
            "قبل إنهاء المقابلة",
            "إغلاق الأسئلة المفتوحة",
            "غير محسومة",
            "افتراضات أو قرارات",
            "خارج النطاق",
        }
        checkpoint_phrases = checkpoint_phrases_en | checkpoint_phrases_ar
        for message in reversed(messages):
            if message.role != "assistant":
                continue
            text = str(message.content or "").lower()
            if any(phrase in text for phrase in checkpoint_phrases):
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
            answer = str(latest_user_answer or "").strip()
            if language == "ar":
                return (
                    "ممتاز، خلّينا نوضّح الصورة أكثر ونكمّل. "
                    f"بالنسبة للي ذكرته ( {answer} )، إيه أهم هدف أو ميزة لازم نثبتها أولاً؟"
                )
            return (
                "Great, let's clarify this and keep moving. "
                f"Regarding what you mentioned ( {answer} ), what is the most important goal or feature to lock first?"
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
    def _initial_question(language: str) -> Dict[str, Any]:
        initial_coverage = dict(_ZERO_COVERAGE)
        if language == "ar":
            return {
                "question": "أهلاً بك. أنا هنا لمساعدتك في جمع متطلبات مشروعك. ماذا تود أن تبني اليوم؟",
                "stage": "discovery",
                "done": False,
                "suggested_answers": [],
                "summary": "",
                "coverage": initial_coverage,
            }
        return {
            "question": "Welcome. I'm here to help gather requirements for your project. What would you like to build today?",
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
    async def _format_conversation_windowed(messages: List[ChatMessage]) -> str:
        total = len(messages)
        recent = messages[-_MAX_RECENT_MESSAGES:]

        lines: List[str] = []
        omitted_messages = messages[:-len(recent)] if len(recent) < total else []
        
        if omitted_messages:
            from backend.services.summarize_task import summarize_old_messages
            # Determine language based on last few messages
            lang = "en"
            for msg in recent[-5:]:
                if _ARABIC_CHAR_PATTERN.search(str(msg.content)):
                    lang = "ar"
                    break
            
            summary = await summarize_old_messages(omitted_messages, lang)
            if summary:
                lines.append(f"[System Summary of previous {len(omitted_messages)} messages]: {summary}")
            else:
                lines.append(f"[Older conversation omitted: {len(omitted_messages)} messages. Use previous summary/coverage as source of truth.]")

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
        """Check if two requirements are similar using token-set overlap (Jaccard)."""
        left_norm = cls._normalize_requirement(left)
        right_norm = cls._normalize_requirement(right)

        if not left_norm or not right_norm:
            return False
        if left_norm == right_norm:
            return True

        # Fuzzy match: Jaccard similarity on word tokens
        left_tokens = set(left_norm.split())
        right_tokens = set(right_norm.split())
        if not left_tokens or not right_tokens:
            return False
        intersection = left_tokens & right_tokens
        union = left_tokens | right_tokens
        return (len(intersection) / len(union)) >= 0.6

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
        import json_repair
        payload = str(raw or "").strip()
        if not payload:
            logger.warning("Empty interview JSON response")
            return {}
        try:
            # Use json_repair to handle truncated or malformed JSON
            parsed_response = json_repair.loads(payload)
            if not isinstance(parsed_response, dict):
                raise ValueError("Parsed JSON is not a dictionary")
            return parsed_response
        except Exception as e:
            logger.error(f"Failed to parse SRS JSON even with repair: {e}")
            logger.error(f"Raw response was: {payload}")
            # Return a safe fallback instead of crashing
            return {
                "question": "تم استلام تفاصيل كثيرة، جاري معالجتها. هل هناك إضافات أخرى؟",
                "stage": "discovery",
                "done": False,
                "suggested_answers": [],
                "patches": [],
                "coverage": {}
            }

    @staticmethod
    def _extract_fenced_json(payload: str) -> str | None:
        match = re.fullmatch(r"```(?:json)?\s*(\{[\s\S]*\}|\[[\s\S]*\])\s*```", payload, flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _extract_balanced_json(payload: str) -> str | None:
        start = payload.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escaped = False
        for idx in range(start, len(payload)):
            char = payload[idx]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return payload[start : idx + 1]
        return None
