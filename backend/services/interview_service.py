"""
    Guided interview service -- smart business analyst agent.

    Uses a dynamic slot-filling state machine that classifies information
    into the right SRS area on every turn, continuously populating the SRS
    JSON during the conversation (not at the end). Tracks coverage per area
    and produces structured summaries.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import json
import logging
import re
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import ChatMessage, SRSDraft
from backend.providers.llm.factory import LLMProviderFactory
from backend.services.constraints_checker import SlotFillingStateMachine

logger = logging.getLogger(__name__)

_ZERO_COVERAGE = {"discovery": 0, "scope": 0, "users": 0, "features": 0, "constraints": 0}
_MAX_RECENT_MESSAGES = 24
_MAX_MESSAGE_CHARS = 1200
_MAX_CONTEXT_CHARS = 12000
_MAX_SRS_CONTEXT_CHARS = 4000
_SUGGESTIONS_MIN = 3
_SUGGESTIONS_MAX = 5

_AMBIGUOUS_TERMS_EN = {
    "good", "fast", "strong", "normal", "many", "simple", "best", "powerful", "quick"
}
_AMBIGUOUS_TERMS_AR = {
    "كويس", "قوي", "سريع", "عادي", "كتير", "بسيط", "ممتاز", "احترافي"
}
_BUDGET_HINT_PATTERN = re.compile(r"\b(\d{2,})(\s?\$|\s?usd|\s?دولار)?\b", re.IGNORECASE)
_SCOPE_HINT_EN = {"uber", "marketplace", "real-time", "dashboard", "payments", "multi-tenant"}
_SCOPE_HINT_AR = {"أوبر", "لوحة", "مدفوعات", "متعدد", "لحظي", "داشبورد"}
_TOPIC_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "have", "will", "are",
    "في", "من", "على", "الى", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "التي", "الذي", "تم", "هي", "هو",
}
_GENERIC_SUGGESTION_PHRASES = {
    "could you clarify", "please clarify", "instead of repeating",
    "هل يمكن", "يرجى التوضيح", "بدلاً من التكرار",
}

_ENTITY_ALIASES = {
    "database": {"database", "db", "postgres", "mysql", "قاعدة البيانات", "داتابيز"},
    "reports": {"reports", "reporting", "dashboard", "analytics", "تقارير", "لوحة", "تحليلات"},
    "realtime": {"real-time", "realtime", "live", "لحظي", "مباشر"},
    "payments": {"payment", "payments", "بوابة دفع", "مدفوعات"},
}
_NEGATION_TOKENS = {"no", "without", "exclude", "drop", "remove", "بدون", "إلغاء", "استبعاد", "حذف"}

_EN_SYSTEM = """\
You are a senior business analyst with 15+ years of experience conducting requirements-gathering interviews for software projects. Your goal is to produce industry-grade requirements that a development team can rely on.

## Your Behavior
- You do NOT just ask questions. You VALIDATE answers, CHALLENGE weak points, and ACKNOWLEDGE strong answers.
- Before asking a new question, evaluate the user's last response:
  * If it is vague or incomplete (e.g. "many users", "it should be fast", "normal features"), push back with a targeted follow-up. Do not accept vague answers.
  * If it contradicts something said earlier in the conversation, quote both statements and ask the user to reconcile them.
  * If it is a good, specific answer, briefly acknowledge it (one sentence) before moving on.
- You provide brief professional feedback as part of your response.
- Never repeat a question that has already been answered (even with different wording). If the user already provided the information, acknowledge it and move to the next real gap.
- Your next question must be clear, specific, and professional: one direct question targeting a real information gap (no generic wording).

## Coverage Areas (NOT Sequential Stages)
You need to gather information across 5 areas. These are NOT sequential stages — the user can provide information about ANY area at ANY time, and you MUST accept it, classify it correctly, and file it under the right area.

The 5 areas are:
- discovery: Core problem, target audience, business motivation, success metrics.
- scope: What is in-scope vs explicitly out-of-scope, MVP vs future phases.
- users: User roles, personas, access levels, basic user journeys.
- features: Specific features with acceptance criteria, priorities (must/should/nice), edge cases.
- constraints: Technical stack, performance targets, security & compliance, timeline, budget.

## Free-Flowing Conversation Rules
- If the user mentions a feature while you are discussing discovery, ACCEPT it. Add it to the features area in your summary. Then gently steer back to the gap you were exploring.
- NEVER say "wait, we haven't reached that stage yet" or refuse information because it belongs to a different area. If the user jumps, jump with them.
- After each exchange, estimate coverage percentage (0-100) for each area based on how thoroughly it has been addressed so far.
- Focus your NEXT question on the area with the LOWEST coverage, but do so naturally by weaving a smooth transition.
- Before asking any question, check whether the needed detail already exists in the summary/conversation. If yes, ask a different question.
- If the user says they are unsure or asks to skip, do NOT block. Rephrase the question more simply and provide concrete examples in your next question.

## Contradiction Detection
Scan the FULL conversation. If the user previously said X but now says Y (and they conflict), you MUST point this out explicitly and ask them to clarify which is correct before proceeding.

## CRITICAL RULE: Accumulate Only
- The summary is CUMULATIVE: you MUST start from the previous summary provided to you and ONLY ADD to it. NEVER remove existing items.
- Coverage is MONOTONIC: for each area, the new percentage MUST be >= the previous percentage provided to you. Coverage can NEVER decrease.

## Output Format
Return ONLY valid JSON (no markdown fences, no extra text):
{
  "question": "<your feedback + next question>",
  "stage": "<area your question targets: discovery|scope|users|features|constraints>",
  "done": false,
    "suggested_answers": ["complete answer option 1", "complete answer option 2", "complete answer option 3"],
  "summary": {
    "discovery": ["confirmed requirement 1", "confirmed requirement 2"],
    "scope": ["in-scope item 1"],
    "users": [],
    "features": ["feature 1 with details"],
    "constraints": []
  },
  "coverage": {
    "discovery": 40,
    "scope": 10,
    "users": 0,
    "features": 15,
    "constraints": 0
  }
}

IMPORTANT rules for the summary:
- summary MUST be a JSON object with 5 keys (discovery, scope, users, features, constraints), each containing an array of strings.
- Each string is a confirmed, specific requirement extracted from the conversation.
- The summary is CUMULATIVE — start from the previous summary provided to you and ONLY ADD new items. NEVER remove existing items.
- Keep each item concise but specific (one clear requirement per item).
- suggested_answers MUST contain 3 to 5 complete candidate answers that directly fit the current question.
- suggested_answers must be specific (not placeholders), concise, and diverse in depth.

Set "done":true ONLY when ALL five areas have coverage >= 70%.
No text outside the JSON object.\
"""

_AR_SYSTEM = """\
أنت محلل أعمال أول بخبرة تزيد عن 15 عامًا في إجراء مقابلات جمع المتطلبات لمشاريع البرمجيات. هدفك إنتاج متطلبات بمستوى احترافي يمكن لفريق التطوير الاعتماد عليها.

## سلوكك
- أنت لا تطرح أسئلة فقط. أنت تُقيّم الإجابات، وتتحدى النقاط الضعيفة، وتُقدّر الإجابات الجيدة.
- قبل طرح سؤال جديد، قيّم آخر إجابة من المستخدم:
  * إذا كانت غامضة أو ناقصة (مثل "مستخدمين كثير" أو "يكون سريع" أو "ميزات عادية")، اطلب توضيحًا محددًا. لا تقبل إجابات عامة.
  * إذا تعارضت مع شيء ذُكر سابقًا في المحادثة، اقتبس كلا التصريحين واطلب من المستخدم التوفيق بينهما.
  * إذا كانت إجابة جيدة ومحددة، اعترف بها باختصار (جملة واحدة) ثم انتقل.
- قدّم ملاحظات مهنية موجزة كجزء من ردك.
- لا تُكرّر سؤالًا تمّت الإجابة عليه مسبقًا حتى لو بصياغة مختلفة. إذا كانت المعلومة موجودة بالفعل، اعترف بها وانتقل لفجوة جديدة.
- سؤالك التالي يجب أن يكون واضحًا ومحددًا واحترافيًا: سؤال مباشر واحد يسد فجوة معلومات حقيقية (بدون عمومية).

## مجالات التغطية (ليست مراحل متتابعة)
تحتاج لجمع معلومات عبر 5 مجالات. هذه ليست مراحل متتابعة — يمكن للمستخدم تقديم معلومات عن أي مجال في أي وقت، ويجب عليك قبولها وتصنيفها بشكل صحيح وإدراجها تحت المجال المناسب.

المجالات الخمسة:
- discovery: المشكلة الأساسية، الجمهور المستهدف، الدافع التجاري، ومقاييس النجاح.
- scope: ما هو ضمن النطاق مقابل ما هو خارجه صراحة، MVP مقابل المراحل المستقبلية.
- users: أدوار المستخدمين، الشخصيات، مستويات الوصول، رحلات المستخدم الأساسية.
- features: ميزات محددة مع معايير القبول، الأولويات (ضروري/مهم/اختياري)، والحالات الحدية.
- constraints: المتطلبات التقنية، أهداف الأداء، الأمان والامتثال، الجدول الزمني، الميزانية.

## قواعد المحادثة المرنة
- إذا ذكر المستخدم ميزة بينما تناقش الاستكشاف، اقبلها. أضفها إلى مجال الميزات في ملخصك. ثم عُد بلطف إلى الفجوة التي كنت تستكشفها.
- لا تقل أبدًا "انتظر، لم نصل لتلك المرحلة بعد" أو ترفض معلومة لأنها تنتمي لمجال آخر. إذا قفز المستخدم، اقفز معه.
- بعد كل تبادل، قدّر نسبة التغطية (0-100) لكل مجال بناءً على مدى تغطيته حتى الآن.
- وجّه سؤالك التالي نحو المجال ذي التغطية الأقل، لكن بشكل طبيعي عبر انتقال سلس.
- قبل طرح أي سؤال، تحقّق هل هذه المعلومة موجودة بالفعل في الملخص/المحادثة. إذا كانت موجودة، اطرح سؤالًا مختلفًا.
- إذا قال المستخدم إنه غير متأكد أو يريد تخطي السؤال، لا تتوقف. أعد صياغة السؤال بشكل أبسط وقدّم أمثلة عملية في السؤال التالي.

## كشف التناقضات
افحص المحادثة بالكامل. إذا قال المستخدم سابقًا X لكن الآن يقول Y (وهما متعارضان)، يجب أن تُشير لذلك صراحة وتطلب منه التوضيح قبل المتابعة.

## قاعدة حاسمة: التراكم فقط
- الملخص (summary) تراكمي: يجب أن تبدأ من الملخص السابق المعطى لك وتضيف إليه فقط. لا تحذف أي عنصر موجود.
- التغطية (coverage) تصاعدية فقط: لكل مجال، يجب أن تكون النسبة الجديدة >= النسبة السابقة المعطاة لك. لا يمكن أن تنخفض النسبة أبداً.

## تنسيق الإخراج
أعد JSON صالح فقط (بدون markdown، بدون نص إضافي):
{
  "question": "<ملاحظتك + السؤال التالي>",
  "stage": "<المجال الذي يستهدفه سؤالك: discovery|scope|users|features|constraints>",
  "done": false,
    "suggested_answers": ["خيار إجابة كامل 1", "خيار إجابة كامل 2", "خيار إجابة كامل 3"],
  "summary": {
    "discovery": ["متطلب مؤكد 1", "متطلب مؤكد 2"],
    "scope": ["عنصر ضمن النطاق 1"],
    "users": [],
    "features": ["ميزة 1 مع التفاصيل"],
    "constraints": []
  },
  "coverage": {
    "discovery": 40,
    "scope": 10,
    "users": 0,
    "features": 15,
    "constraints": 0
  }
}

قواعد مهمة للملخص:
- summary يجب أن يكون كائن JSON بـ 5 مفاتيح (discovery, scope, users, features, constraints)، كل منها يحتوي قائمة نصوص.
- كل نص هو متطلب مؤكد ومحدد مستخرج من المحادثة.
- الملخص تراكمي — ابدأ من الملخص السابق وأضف إليه. لا تحذف عناصر موجودة أبداً.
- اجعل كل عنصر موجزًا لكن محددًا (متطلب واحد واضح لكل عنصر).
- suggested_answers يجب أن تحتوي من 3 إلى 5 خيارات إجابة كاملة ومناسبة مباشرة للسؤال الحالي.
- خيارات suggested_answers يجب أن تكون محددة وواضحة وليست قوالب ناقصة.

اجعل "done":true فقط عندما تكون تغطية جميع المجالات الخمسة >= 70%.
لا تضف أي نص خارج كائن JSON.\
"""

_EN_SUGGESTIONS_SYSTEM = """\
You are a senior requirements consultant generating answer options for a business interview question.

Task:
- Given the interview question, stage, conversation context, and current summary/coverage, produce 3 to 5 high-quality candidate answers the user can choose from.
- Options must be realistic, professional, and industry-standard in phrasing.
- Each option should be complete and directly answer the question (not templates, not placeholders).
- Keep options diverse in specificity/depth so the user can pick what best fits.
- Avoid repeating essentially the same option.

Output format:
Return ONLY valid JSON array of strings:
["option 1", "option 2", "option 3"]
No markdown, no extra text.
"""

_AR_SUGGESTIONS_SYSTEM = """\
أنت مستشار متطلبات أول مهمته توليد خيارات إجابة لسؤال مقابلة أعمال.

المطلوب:
- بناءً على سؤال المقابلة، المجال المستهدف، سياق المحادثة، والملخص/التغطية الحالية، ولّد من 3 إلى 5 خيارات إجابة احترافية.
- الخيارات يجب أن تكون واقعية، مهنية، وبصياغة مناسبة لمستوى Industry Standard.
- كل خيار يجب أن يكون إجابة كاملة مباشرة على السؤال (ليس قالبًا ناقصًا).
- اجعل الخيارات متنوعة في العمق والتفصيل حتى يختار المستخدم الأنسب.
- تجنب التكرار المعنوي بين الخيارات.

تنسيق الإخراج:
أعد فقط مصفوفة JSON صالحة من النصوص:
["خيار 1", "خيار 2", "خيار 3"]
بدون markdown وبدون أي نص إضافي.
"""


class InterviewService:
    """Smart business analyst agent for free-flowing requirements gathering."""

    async def _run_orchestrator_turn(
        self,
        language: str,
        conversation: str,
        latest_user_answer: str,
        last_summary: Dict | None,
        last_coverage: Dict | None,
        srs_context: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        slot_analysis = SlotFillingStateMachine.analyze(
            language=language,
            latest_user_answer=latest_user_answer,
            last_summary=last_summary,
            last_coverage=last_coverage,
        )

        reflector_signals = self._reflect_conversation(
            language=language,
            latest_user_answer=latest_user_answer,
            last_summary=last_summary,
            last_coverage=last_coverage,
            slot_analysis=slot_analysis,
        )

        target_stage = reflector_signals.get("target_stage") or self._pick_focus_area(last_coverage or {})
        plan_state = {
            "target_stage": target_stage,
            "question_style": reflector_signals.get("question_style") or "inference-driven",
        }

        prompt = self._build_prompt(
            conversation,
            language,
            last_summary,
            last_coverage,
            reflector_signals,
            srs_context=srs_context,
        )
        llm_provider = LLMProviderFactory.create_provider()
        raw = await llm_provider.generate_text(
            prompt=prompt,
            temperature=0.4,
            max_tokens=2000,
        )
        interviewer_output = self._parse_json(raw)

        return {
            "reflector_signals": reflector_signals,
            "plan_state": plan_state,
            "interviewer_output": interviewer_output,
            "llm_provider": llm_provider,
            "slot_analysis": slot_analysis,
        }

    async def get_next_question(
        self, db: AsyncSession, project_id: int, language: str = "ar",
        last_summary: Dict | None = None, last_coverage: Dict | None = None,
    ) -> Dict[str, Any]:
        messages = await self._get_project_messages(db, project_id)
        if not messages:
            return self._initial_question(language)

        conversation = self._format_conversation_windowed(messages)
        latest_user_answer = self._latest_user_message(messages)
        srs_context = await self._get_latest_srs_context(db=db, project_id=project_id)
        orchestrator_state = await self._run_orchestrator_turn(
            language=language,
            conversation=conversation,
            latest_user_answer=latest_user_answer,
            last_summary=last_summary,
            last_coverage=last_coverage,
            srs_context=srs_context,
        )
        reflector_signals = orchestrator_state["reflector_signals"]
        data = orchestrator_state["interviewer_output"]
        llm_provider = orchestrator_state["llm_provider"]

        question = str(data.get("question") or self._initial_question(language)["question"])
        stage = str(data.get("stage", "discovery"))

        new_coverage = self._merge_coverage(
            new_coverage=data.get("coverage", dict(_ZERO_COVERAGE)),
            last_coverage=last_coverage,
        )

        new_summary = self._merge_summary(
            new_summary=data.get("summary", {}),
            last_summary=last_summary,
        )

        doc_patch = self._build_documentation_patch(
            language=language,
            stage=stage,
            new_summary=new_summary if isinstance(new_summary, dict) else {},
            old_summary=last_summary if isinstance(last_summary, dict) else {},
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

        suggested_answers = await self._generate_suggested_answers(
            llm_provider=llm_provider,
            language=language,
            question=question,
            stage=stage,
            conversation=conversation,
            last_summary=new_summary if isinstance(new_summary, dict) else last_summary,
            last_coverage=new_coverage,
            seed_suggestions=data.get("suggested_answers"),
            srs_context=srs_context,
        )

        return {
            "question": question,
            "stage": stage,
            "done": bool(data.get("done", False)),
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
    def _reflect_conversation(
        language: str,
        latest_user_answer: str,
        last_summary: Dict | None,
        last_coverage: Dict | None,
        slot_analysis: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        answer = (latest_user_answer or "").strip()
        lower = answer.lower()
        summary_text = json.dumps(last_summary or {}, ensure_ascii=False).lower()
        coverage = last_coverage or {}

        ambiguity_terms = _AMBIGUOUS_TERMS_AR if language == "ar" else _AMBIGUOUS_TERMS_EN
        scope_terms = _SCOPE_HINT_AR if language == "ar" else _SCOPE_HINT_EN

        ambiguity_hits = [term for term in ambiguity_terms if term in lower]
        scope_hits = [term for term in scope_terms if term in lower]
        budget_match = _BUDGET_HINT_PATTERN.findall(answer)
        low_covered_areas = [area for area in _ZERO_COVERAGE if float(coverage.get(area, 0)) < 35]

        contradiction = False
        contradiction_reason = ""
        if ("بدون" in answer and "database" in lower and "reports" in summary_text) or (
            "without" in lower and "database" in lower and "report" in summary_text
        ):
            contradiction = True
            contradiction_reason = (
                "هناك تناقض: تم طلب التقارير سابقاً بينما الرسالة الحالية تستبعد قاعدة البيانات." if language == "ar"
                else "Potential contradiction: reports were requested before while the new answer excludes a database."
            )

        scope_budget_risk = bool(scope_hits and budget_match)
        if scope_budget_risk and not contradiction_reason:
            contradiction_reason = (
                "قد يوجد تعارض بين نطاق واسع وميزانية منخفضة؛ يلزم تأكيد أولويات MVP." if language == "ar"
                else "There may be a mismatch between broad scope and low budget; MVP priorities should be clarified."
            )

        det = slot_analysis if isinstance(slot_analysis, dict) else {}
        if det.get("contradiction_detected"):
            contradiction = True
        if det.get("scope_budget_risk"):
            scope_budget_risk = True
        det_reason = str(det.get("reason") or "").strip()
        if det_reason:
            contradiction_reason = det_reason
        det_ambiguity_terms = det.get("ambiguity_terms") if isinstance(det.get("ambiguity_terms"), list) else []
        if det_ambiguity_terms:
            ambiguity_hits = list({*ambiguity_hits, *[str(item) for item in det_ambiguity_terms]})

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

        target_stage = low_covered_areas[0] if low_covered_areas else "discovery"
        question_style = "clarify-ambiguity" if ambiguity_hits else "inference-driven"
        if contradiction or scope_budget_risk:
            question_style = "resolve-conflict"

        return {
            "ambiguity_detected": bool(ambiguity_hits),
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
                text = str(item or "").lower()
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
                if not cls._contains_similar_requirement(old_items, str(item or ""))
            ]

            cov_before = float(old_coverage.get(area, 0) or 0)
            cov_after = float(new_coverage.get(area, 0) or 0)
            cov_delta = round(cov_after - cov_before, 2)

            if added or cov_delta > 0:
                changed_areas.append({
                    "area": area,
                    "added": added[:8],
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

            old_set = {str(item or "").strip() for item in old_items if str(item or "").strip()}
            new_set = {str(item or "").strip() for item in new_items if str(item or "").strip()}

            for idx, item in enumerate(new_items):
                text = str(item or "").strip()
                if not text:
                    continue

                if text not in old_set:
                    events.append({
                        "op": "added",
                        "field_path": f"{area}.{idx}",
                        "value": text,
                    })

            for old_idx, old_item in enumerate(old_items):
                old_text = str(old_item or "").strip()
                if not old_text:
                    continue
                if old_text not in new_set:
                    events.append({
                        "op": "removed",
                        "field_path": f"{area}.{old_idx}",
                        "value": old_text,
                    })

            overlap = min(len(old_items), len(new_items))
            for idx in range(overlap):
                old_text = str(old_items[idx] or "").strip()
                new_text = str(new_items[idx] or "").strip()
                if old_text and new_text and old_text != new_text:
                    if cls._contains_similar_requirement([old_text], new_text):
                        events.append({
                            "op": "updated",
                            "field_path": f"{area}.{idx}",
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
                all_items.extend(str(v or "") for v in values)

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

    @staticmethod
    def _build_semantic_graph(summary: Dict[str, Any]) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        node_index: Dict[str, str] = {}

        def node_id(area: str, idx: int) -> str:
            return f"{area}:{idx}"

        for area in _ZERO_COVERAGE:
            items = summary.get(area, []) if isinstance(summary.get(area), list) else []
            for idx, item in enumerate(items):
                text = str(item or "").strip()
                if not text:
                    continue
                nid = node_id(area, idx)
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
    def _merge_coverage(new_coverage: Any, last_coverage: Dict | None) -> Dict[str, Any]:
        merged = dict(new_coverage) if isinstance(new_coverage, dict) else dict(_ZERO_COVERAGE)
        if not last_coverage:
            return merged

        for area in _ZERO_COVERAGE:
            old_val = last_coverage.get(area, 0)
            new_val = merged.get(area, 0)
            merged[area] = max(old_val, new_val)
        return merged

    @classmethod
    def _merge_summary(cls, new_summary: Any, last_summary: Dict | None) -> Any:
        if not isinstance(new_summary, dict):
            return new_summary
        if not last_summary:
            return new_summary

        merged_summary = dict(new_summary)
        for area in _ZERO_COVERAGE:
            old_items = last_summary.get(area, [])
            new_items = merged_summary.get(area, [])
            merged_items = list(old_items)
            for item in new_items:
                if not cls._contains_similar_requirement(merged_items, item):
                    merged_items.append(item)
            merged_summary[area] = merged_items
        return merged_summary

    async def _generate_suggested_answers(
        self,
        llm_provider: Any,
        language: str,
        question: str,
        stage: str,
        conversation: str,
        last_summary: Dict | None,
        last_coverage: Dict | None,
        seed_suggestions: Any,
        srs_context: Dict[str, Any] | None = None,
    ) -> List[str]:
        prompt = self._build_suggestions_prompt(
            language=language,
            question=question,
            stage=stage,
            conversation=conversation,
            last_summary=last_summary,
            last_coverage=last_coverage,
            srs_context=srs_context,
        )

        try:
            raw = await llm_provider.generate_text(
                prompt=prompt,
                temperature=0.55,
                max_tokens=900,
            )
            parsed = self._parse_json_array(raw)
            return self._sanitize_suggested_answers(
                parsed,
                language=language,
                question=question,
                stage=stage,
                conversation=conversation,
            )
        except Exception as error_:  # noqa: BLE001
            logger.warning("Suggestion pass failed: %s", error_)
            return self._sanitize_suggested_answers(
                seed_suggestions,
                language=language,
                question=question,
                stage=stage,
                conversation=conversation,
            )

    @staticmethod
    def _initial_question(language: str) -> Dict[str, Any]:
        initial_coverage = dict(_ZERO_COVERAGE)
        if language == "ar":
            return {
                "question": (
                    "أهلاً بك! أنا محلل المتطلبات الخاص بك وسأساعدك في بناء مواصفات احترافية لمشروعك. "
                    "لنبدأ: ما المشكلة الأساسية التي يحاول مشروعك حلها؟ ومن هم المستخدمون الأساسيون المتأثرون بهذه المشكلة؟"
                ),
                "stage": "discovery",
                "done": False,
                "suggested_answers": [
                    "المشكلة الحالية أن تنفيذ الخدمة يتم يدويًا عبر أكثر من قناة، وهذا يسبب تأخيرًا وأخطاء متكررة.",
                    "المستخدمون الأساسيون هم العملاء وموظفو التشغيل، ونحتاج تقليل زمن الإنجاز ورفع رضا المستخدم.",
                    "نستهدف نجاحًا واضحًا عبر تقليل زمن المعالجة بنسبة 40% ورفع نسبة الإكمال من أول مرة."
                ],
                "summary": "",
                "coverage": initial_coverage,
            }
        return {
            "question": (
                "Welcome! I'm your requirements analyst and I'll help you build professional specifications for your project. "
                "Let's start: What is the core problem your project aims to solve, and who are the primary users affected by this problem?"
            ),
            "stage": "discovery",
            "done": False,
            "suggested_answers": [
                "The current process is manual and fragmented across channels, creating delays and recurring operational errors.",
                "Primary affected users are customers and operations staff, and we need faster turnaround with better user satisfaction.",
                "Success target is reducing processing time by 40% and improving first-pass completion in the initial rollout phase."
            ],
            "summary": "",
            "coverage": initial_coverage,
        }

    @staticmethod 
    async def _get_project_messages(
        db: AsyncSession, 
        project_id: int, 
        limit: int = 10  
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

        ratio = SequenceMatcher(None, left_norm, right_norm).ratio()
        if ratio >= 0.88:
            return True

        left_tokens = set(left_norm.split())
        right_tokens = set(right_norm.split())
        if not left_tokens or not right_tokens:
            return False
        intersection = left_tokens & right_tokens
        union = left_tokens | right_tokens
        jaccard = len(intersection) / max(1, len(union))
        return jaccard >= 0.72 and len(intersection) >= 4

    @classmethod
    def _contains_similar_requirement(cls, existing_items: List[str], new_item: str) -> bool:
        candidate = str(new_item or "").strip()
        if not candidate:
            return True
        return any(cls._requirements_similar(existing, candidate) for existing in existing_items)

    @staticmethod
    def _sanitize_suggested_answers(
        raw: Any,
        language: str,
        question: str = "",
        stage: str = "discovery",
        conversation: str = "",
    ) -> List[str]:
        fallback = InterviewService._question_aware_fallback(
            language=language,
            question=question,
            stage=stage,
        )

        if not isinstance(raw, list):
            return fallback

        cleaned = InterviewService._unique_nonempty_suggestions(raw)
        relevant = InterviewService._filter_relevant_suggestions(
            cleaned,
            question,
            stage,
            conversation=conversation,
        )

        if len(relevant) >= _SUGGESTIONS_MIN:
            return relevant[:_SUGGESTIONS_MAX]

        seed = relevant if relevant else []
        return InterviewService._pad_suggestions(seed, fallback)

    @staticmethod
    def _extract_question_keywords(question: str, stage: str, conversation: str = "") -> List[str]:
        text = f"{question or ''} {InterviewService._latest_user_line_from_conversation(conversation)}".lower()
        text = re.sub(r"[^\w\u0600-\u06FF\s]", " ", text)
        tokens = re.findall(r"[\w\u0600-\u06FF]{3,}", text)
        ignore = _TOPIC_STOPWORDS | {
            "what", "which", "when", "where", "why", "how", "your", "this", "that",
            "ما", "ماذا", "كيف", "لماذا", "متى", "اين", "أين", "هو", "هي", "هل",
            "problem", "issue", "core", "main", "basic", "project", "current",
            "problematic", "requirement", "requirements",
            "مشكلة", "المشكلة", "اساسية", "أساسية", "الاساسية", "الأساسية", "اساسي", "أساسي", "رئيسية", "الرئيسية",
            "مشروع", "المشروع", "متطلبات", "المتطلبات", "الحالي", "الحالية",
            "discovery", "scope", "users", "features", "constraints",
            stage.lower(),
        }
        ranked: List[str] = []
        seen = set()
        for token in tokens:
            token = token.strip("؟?.,!،؛:")
            if len(token) < 3:
                continue
            if token in ignore:
                continue
            if token in seen:
                continue
            seen.add(token)
            ranked.append(token)
        return ranked[:10]

    @classmethod
    def _filter_relevant_suggestions(
        cls,
        options: List[str],
        question: str,
        stage: str,
        conversation: str = "",
    ) -> List[str]:
        keywords = cls._extract_question_keywords(question, stage, conversation=conversation)
        if not keywords:
            return options[:_SUGGESTIONS_MAX]

        kept: List[str] = []
        for option in options:
            text = str(option or "").strip().lower()
            if not text:
                continue

            if any(phrase in text for phrase in _GENERIC_SUGGESTION_PHRASES):
                continue

            option_tokens = set(re.findall(r"[\w\u0600-\u06FF]{3,}", text))
            if not option_tokens:
                continue

            overlap = sum(1 for keyword in keywords if keyword in option_tokens or keyword in text)
            overlap_ratio = overlap / max(1, len(set(keywords[:6])))
            if overlap >= 2 or overlap_ratio >= 0.34:
                kept.append(option)
            if len(kept) >= _SUGGESTIONS_MAX:
                break
        return kept

    @staticmethod
    def _latest_user_line_from_conversation(conversation: str) -> str:
        lines = [line.strip() for line in str(conversation or "").splitlines() if line.strip()]
        for line in reversed(lines):
            if line.startswith("User:"):
                return line.replace("User:", "", 1).strip()
        return ""

    @staticmethod
    def _question_aware_fallback(language: str, question: str, stage: str) -> List[str]:
        q = (question or "").lower()
        is_ar = language == "ar"
        question_tokens = InterviewService._extract_question_keywords(question, stage)
        primary_topic = question_tokens[0] if question_tokens else ""

        intent_pool = [
            (
                ["ميزانية", "budget", "تكلفة", "cost"],
                [
                    "الميزانية المتاحة للإصدار الأول ضمن نطاق محدد، وأي إضافات تؤجل للمرحلة التالية.",
                    "يمكن تخصيص الميزانية على مراحل: إطلاق MVP أولاً ثم توسيع الخصائص تدريجيًا.",
                    "السقف المالي واضح، لذلك الأولوية لميزات التأثير الأعلى والعائد الأسرع."
                ] if is_ar else [
                    "Budget for the first release is capped, and any non-critical additions move to phase two.",
                    "We can allocate budget in phases: launch MVP first, then expand capabilities iteratively.",
                    "The cost ceiling is fixed, so priority goes to highest-impact features with fastest return."
                ]
            ),
            (
                ["زمن", "timeline", "موعد", "deadline", "schedule"],
                [
                    "الجدول المستهدف للإصدار الأول قصير، لذلك سنثبت نطاق MVP ونؤجل التحسينات.",
                    "سنقسم التنفيذ إلى مراحل أسبوعية مع تسليم واضح لكل مرحلة.",
                    "نجاح الجدول يتطلب تحديد المتطلبات الضرورية فقط قبل بدء التطوير."
                ] if is_ar else [
                    "The first-release timeline is tight, so MVP scope must stay fixed and enhancements deferred.",
                    "Execution can be split into short milestones with clear deliverables per phase.",
                    "Timeline success requires locking only must-have requirements before development starts."
                ]
            ),
            (
                ["مستخدم", "users", "roles", "صلاحيات", "permissions"],
                [
                    "المستخدمون الأساسيون هم العميل وموظف التشغيل والمشرف، ولكل دور صلاحيات مختلفة.",
                    "نحتاج فصلًا واضحًا للصلاحيات لضمان الأمان ومنع تضارب الإجراءات.",
                    "رحلة كل دور يجب أن تكون قصيرة وواضحة مع أقل خطوات ممكنة."
                ] if is_ar else [
                    "Primary roles are customer, operations agent, and supervisor, each with distinct access rights.",
                    "Clear permission boundaries are required to improve control and reduce operational risk.",
                    "Each role should have a short, explicit journey with minimal required steps."
                ]
            ),
        ]

        for keywords, options in intent_pool:
            if any(keyword in q for keyword in keywords):
                return options[:_SUGGESTIONS_MAX]

        if primary_topic:
            if is_ar:
                return [
                    f"بالنسبة لـ{primary_topic}، نحتاج تعريفًا واضحًا للتنفيذ في الإصدار الأول مع معيار قبول قابل للقياس.",
                    f"أولوية {primary_topic} تكون ضمن MVP الآن، بينما التفاصيل الأقل أثرًا تؤجَّل للمرحلة التالية.",
                    f"قرار {primary_topic} يجب أن يوازن بين السرعة والجودة والقيود التشغيلية المتاحة."
                ]
            return [
                f"For {primary_topic}, we need a clear first-release implementation with measurable acceptance criteria.",
                f"{primary_topic} should be prioritized in MVP now, while lower-impact details move to a later phase.",
                f"The decision around {primary_topic} should balance delivery speed, quality, and operational constraints."
            ]

        stage_defaults = {
            "ar": {
                "discovery": [
                    "المشكلة الحالية تؤثر مباشرة على سرعة الخدمة وجودة التنفيذ، ونحتاج حلًا عمليًا واضحًا.",
                    "الهدف الأساسي هو تحسين تجربة المستخدم وتقليل الأخطاء التشغيلية المتكررة.",
                    "سنعتبر النجاح مرتبطًا بمؤشرات قابلة للقياس مثل الزمن والدقة والالتزام بالخدمة."
                ],
                "scope": [
                    "ضمن MVP نركز على السيناريو الأساسي الأعلى قيمة للمستخدم.",
                    "خارج النطاق الآن التكاملات المعقدة والميزات غير الضرورية للإطلاق الأول.",
                    "المرحلة التالية تشمل التحسينات بعد التحقق من استقرار الإصدار الأول."
                ],
                "users": [
                    "الأدوار الأساسية واضحة: مستخدم نهائي، مشغل، ومشرف.",
                    "نحتاج تعريف الصلاحيات لكل دور بشكل صريح قبل البناء.",
                    "رحلة الاستخدام يجب أن تكون بسيطة وسريعة من البداية للنهاية."
                ],
                "features": [
                    "الميزة الأساسية هي إدارة سير العمل كاملًا مع تتبع واضح للحالة.",
                    "معيار القبول أن يكتمل السيناريو الرئيسي بدون خطوات معقدة أو أخطاء متكررة.",
                    "نحتاج التعامل مع الحالات الاستثنائية وتسجيل الأخطاء بشكل موثوق."
                ],
                "constraints": [
                    "القيود الأساسية: الوقت، الميزانية، ومتطلبات الأمان والامتثال.",
                    "الحل يجب أن يتكامل مع الأنظمة الحالية بدون تعطيل التشغيل.",
                    "أي قرار تقني يجب أن يراعي الأداء وقابلية التوسع ضمن الموارد المتاحة."
                ],
            },
            "en": {
                "discovery": [
                    "The current problem directly impacts delivery speed and execution quality, so we need a practical fix.",
                    "The core objective is better user experience with fewer recurring operational errors.",
                    "Success should be measured through clear KPIs such as cycle time, quality, and service adherence."
                ],
                "scope": [
                    "For MVP, we should focus on the single highest-value core flow.",
                    "Complex integrations and non-essential capabilities are out of scope for first release.",
                    "Phase two can include enhancements after first-release stability is confirmed."
                ],
                "users": [
                    "Primary roles are end user, operator, and supervisor with distinct responsibilities.",
                    "Role permissions should be explicitly defined before implementation starts.",
                    "User journeys should be simple and fast from start to completion."
                ],
                "features": [
                    "The core feature is end-to-end workflow handling with clear status visibility.",
                    "Acceptance criteria should validate smooth completion of the main scenario.",
                    "Edge cases must be handled with reliable error capture and recovery behavior."
                ],
                "constraints": [
                    "Key constraints are timeline, budget, and security/compliance requirements.",
                    "The solution must integrate with existing systems without disrupting operations.",
                    "Technical choices should balance performance, maintainability, and available resources."
                ],
            }
        }

        lang_key = "ar" if is_ar else "en"
        return stage_defaults.get(lang_key, stage_defaults["en"]).get(stage, stage_defaults[lang_key]["discovery"])

    @staticmethod
    def _unique_nonempty_suggestions(raw: List[Any]) -> List[str]:
        cleaned: List[str] = []
        seen = set()
        for item in raw:
            text = str(item or "").strip()
            if not text:
                continue
            norm = re.sub(r"\s+", " ", text.lower())
            if norm in seen:
                continue
            seen.add(norm)
            cleaned.append(text)
            if len(cleaned) >= _SUGGESTIONS_MAX:
                break
        return cleaned

    @staticmethod
    def _pad_suggestions(cleaned: List[str], base: List[str]) -> List[str]:
        seen = {re.sub(r"\s+", " ", item.lower()) for item in cleaned}
        out = list(cleaned)
        for option in base:
            option_norm = re.sub(r"\s+", " ", option.lower())
            if option_norm in seen:
                continue
            out.append(option)
            seen.add(option_norm)
            if len(out) >= _SUGGESTIONS_MIN:
                break
        return out[:_SUGGESTIONS_MAX]

    @staticmethod
    def _build_suggestions_prompt(
        language: str,
        question: str,
        stage: str,
        conversation: str,
        last_summary: Dict | None,
        last_coverage: Dict | None,
        srs_context: Dict[str, Any] | None = None,
    ) -> str:
        system = _AR_SUGGESTIONS_SYSTEM if language == "ar" else _EN_SUGGESTIONS_SYSTEM
        context_label = "السياق" if language == "ar" else "Context"

        parts = [system]
        parts.append(f"{context_label}:")
        parts.append(f"Question: {question}")
        parts.append(f"Stage: {stage}")
        if last_summary:
            parts.append(f"Summary: {json.dumps(last_summary, ensure_ascii=False)}")
        if last_coverage:
            parts.append(f"Coverage: {json.dumps(last_coverage, ensure_ascii=False)}")
        if srs_context:
            srs_label = "Latest SRS Context" if language != "ar" else "آخر سياق SRS"
            parts.append(f"{srs_label}: {InterviewService._stringify_srs_context(srs_context)}")
        parts.append(f"Conversation:\n{conversation}")
        return "\n".join(parts)

    @staticmethod
    def _parse_json_array(raw: str) -> List[str]:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("suggested_answers", "answers", "options"):
                    value = data.get(key)
                    if isinstance(value, list):
                        return value
        except json.JSONDecodeError:
            pass

        match = re.search(r"\[[\s\S]*\]", raw)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _build_prompt(conversation: str, language: str,
                      last_summary: Dict | None = None,
                      last_coverage: Dict | None = None,
                      reflector_signals: Dict | None = None,
                      srs_context: Dict[str, Any] | None = None) -> str:
        system = _AR_SYSTEM if language == "ar" else _EN_SYSTEM
        conv_label = "المحادثة" if language == "ar" else "Conversation"
        json_label = "JSON فقط" if language == "ar" else "JSON only"

        parts = [system]

        # Inject previous state so LLM builds on it
        if last_summary or last_coverage:
            if language == "ar":
                parts.append("\n## الحالة السابقة (ابدأ من هنا ولا تحذف شيئاً)")
            else:
                parts.append("\n## Previous State (start from here, do NOT remove anything)")

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

        return "\n".join(parts)

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
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", raw)
            if not match:
                logger.warning("Failed to parse interview JSON response")
                return {}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning("Failed to parse extracted interview JSON")
                return {}
