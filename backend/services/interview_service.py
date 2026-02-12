"""
Guided interview service – smart business analyst agent.
Free-flowing conversation that classifies information into
the right SRS area regardless of when it's mentioned.
Tracks coverage per area and produces structured summaries.
"""
from __future__ import annotations

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

_EN_SYSTEM = """\
You are a senior business analyst with 15+ years of experience conducting requirements-gathering interviews for software projects. Your goal is to produce industry-grade requirements that a development team can rely on.

## Your Behavior
- You do NOT just ask questions. You VALIDATE answers, CHALLENGE weak points, and ACKNOWLEDGE strong answers.
- Before asking a new question, evaluate the user's last response:
  * If it is vague or incomplete (e.g. "many users", "it should be fast", "normal features"), push back with a targeted follow-up. Do not accept vague answers.
  * If it contradicts something said earlier in the conversation, quote both statements and ask the user to reconcile them.
  * If it is a good, specific answer, briefly acknowledge it (one sentence) before moving on.
- You provide brief professional feedback as part of your response.

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

اجعل "done":true فقط عندما تكون تغطية جميع المجالات الخمسة >= 70%.
لا تضف أي نص خارج كائن JSON.\
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

        conversation = self._format_conversation(messages)
        prompt = self._build_prompt(conversation, language, last_summary, last_coverage)
        llm_provider = LLMProviderFactory.create_provider()
        raw = await llm_provider.generate_text(
            prompt=prompt,
            temperature=0.4,
            max_tokens=2000,
        )
        data = self._parse_json(raw)

        # Enforce monotonic coverage: new value must be >= old value
        new_coverage = data.get("coverage", dict(_ZERO_COVERAGE))
        if last_coverage:
            for area in _ZERO_COVERAGE:
                old_val = last_coverage.get(area, 0)
                new_val = new_coverage.get(area, 0)
                new_coverage[area] = max(old_val, new_val)

        # Enforce cumulative summary: never lose existing items
        new_summary = data.get("summary", {})
        if last_summary and isinstance(new_summary, dict):
            for area in _ZERO_COVERAGE:
                old_items = last_summary.get(area, [])
                new_items = new_summary.get(area, [])
                # Merge: keep all old items, add any genuinely new ones
                merged = list(old_items)
                for item in new_items:
                    if item not in merged:
                        merged.append(item)
                new_summary[area] = merged

        return {
            "question": data.get("question") or self._initial_question(language)["question"],
            "stage": data.get("stage", "discovery"),
            "done": bool(data.get("done", False)),
            "summary": new_summary if new_summary else "",
            "coverage": new_coverage,
        }

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
            "summary": "",
            "coverage": initial_coverage,
        }

    @staticmethod
    async def _get_project_messages(db: AsyncSession, project_id: int) -> List[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _format_conversation(messages: List[ChatMessage]) -> str:
        lines = []
        for msg in messages:
            role = msg.role.lower()
            prefix = "User" if role == "user" else "Assistant" if role == "assistant" else "System"
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)

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
