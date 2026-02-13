"""
Guided interview service – smart business analyst agent.
Free-flowing conversation that classifies information into
the right SRS area regardless of when it's mentioned.
Tracks coverage per area and produces structured summaries.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import json
import logging
import re
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import ChatMessage
from backend.providers.llm.factory import LLMProviderFactory

logger = logging.getLogger(__name__)

_ZERO_COVERAGE = {"discovery": 0, "scope": 0, "users": 0, "features": 0, "constraints": 0}
_MAX_RECENT_MESSAGES = 24
_MAX_MESSAGE_CHARS = 1200
_MAX_CONTEXT_CHARS = 12000
_SUGGESTIONS_MIN = 3
_SUGGESTIONS_MAX = 5

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

    async def get_next_question(
        self, db: AsyncSession, project_id: int, language: str = "ar",
        last_summary: Dict | None = None, last_coverage: Dict | None = None,
    ) -> Dict[str, Any]:
        messages = await self._get_project_messages(db, project_id)
        if not messages:
            return self._initial_question(language)

        conversation = self._format_conversation_windowed(messages)
        prompt = self._build_prompt(conversation, language, last_summary, last_coverage)
        llm_provider = LLMProviderFactory.create_provider()
        raw = await llm_provider.generate_text(
            prompt=prompt,
            temperature=0.4,
            max_tokens=2000,
        )
        data = self._parse_json(raw)

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

        suggested_answers = await self._generate_suggested_answers(
            llm_provider=llm_provider,
            language=language,
            question=question,
            stage=stage,
            conversation=conversation,
            last_summary=new_summary if isinstance(new_summary, dict) else last_summary,
            last_coverage=new_coverage,
            seed_suggestions=data.get("suggested_answers"),
        )

        return {
            "question": question,
            "stage": stage,
            "done": bool(data.get("done", False)),
            "suggested_answers": suggested_answers,
            "summary": new_summary if new_summary else "",
            "coverage": new_coverage,
        }

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
    ) -> List[str]:
        prompt = self._build_suggestions_prompt(
            language=language,
            question=question,
            stage=stage,
            conversation=conversation,
            last_summary=last_summary,
            last_coverage=last_coverage,
        )

        try:
            raw = await llm_provider.generate_text(
                prompt=prompt,
                temperature=0.55,
                max_tokens=900,
            )
            parsed = self._parse_json_array(raw)
            return self._sanitize_suggested_answers(parsed, language=language)
        except Exception as error_:  # noqa: BLE001
            logger.warning("Suggestion pass failed: %s", error_)
            return self._sanitize_suggested_answers(seed_suggestions, language=language)

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
    def _sanitize_suggested_answers(raw: Any, language: str) -> List[str]:
        fallback = {
            "ar": [
                "يمكنني توضيح المتطلب بالأثر العملي على المستخدم ومؤشر النجاح المتوقع.",
                "المطلوب في الإصدار الأول هو القيمة الأعلى أثرًا مع حدود واضحة لما هو خارج النطاق.",
                "القيود الأساسية عندنا هي الوقت والجودة والامتثال، وسنرتب الأولويات وفق ذلك."
            ],
            "en": [
                "I can explain the requirement in terms of user impact and measurable success outcome.",
                "For the first release, we should focus on highest-impact scope with explicit out-of-scope boundaries.",
                "Our key constraints are timeline, quality, and compliance, so priorities should align accordingly."
            ]
        }

        if not isinstance(raw, list):
            return fallback.get(language, fallback["en"])

        cleaned = InterviewService._unique_nonempty_suggestions(raw)
        if len(cleaned) >= _SUGGESTIONS_MIN:
            return cleaned[:_SUGGESTIONS_MAX]

        base = fallback.get(language, fallback["en"])
        return InterviewService._pad_suggestions(cleaned, base)

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
                      last_coverage: Dict | None = None) -> str:
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

        parts.append(f"\n{conv_label}:\n{conversation}\n\n{json_label}:")

        return "\n".join(parts)

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
