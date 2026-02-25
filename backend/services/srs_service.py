"""
SRS draft generation and export service.
"""
from __future__ import annotations

import ast
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import Asset, ChatMessage, SRSDraft
from backend.providers.llm.factory import LLMProviderFactory
from backend.services.judging_service import JudgingService
from backend.services.srs_pdf_html_renderer import render_srs_pdf_html
from backend.services.srs_snapshot_cache import SRSSnapshotCache

logger = logging.getLogger(__name__)


class SRSService:
    """Generate and export SRS drafts from project transcripts and chat."""
    def __init__(self):
        self.judging_service = JudgingService()

    async def get_latest_draft(self, db: AsyncSession, project_id: int) -> SRSDraft | None:
        stmt = (
            select(SRSDraft)
            .where(SRSDraft.project_id == project_id)
            .order_by(SRSDraft.version.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_draft(
        self,
        db: AsyncSession,
        project_id: int,
        language: str = "ar",
    ) -> SRSDraft:
        messages = await self._get_project_messages(db, project_id)
        transcript_blocks = await self._get_project_transcripts(db, project_id)
        if not messages and not transcript_blocks:
            raise ValueError("No interview transcripts or chat messages found for this project")

        conversation = self._format_conversation(messages)
        transcripts = self._format_transcripts(transcript_blocks)

        # Quality gate: ensure there is enough content for a meaningful SRS
        self._quality_gate(transcripts, conversation)

        prompt = self._build_prompt(conversation, transcripts, language)

        llm_provider = LLMProviderFactory.create_provider()
        raw = await self._generate_structured_text(
            llm_provider=llm_provider,
            prompt=prompt,
            temperature=0.3,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )
        try:
            content = self._parse_json(raw)
        except ValueError as first_parse_error:
            logger.warning("Initial SRS parse failed for project %s: %s", project_id, first_parse_error)
            repair_prompt = (
                f"{prompt}\n\n"
                "STRICT JSON REPAIR INSTRUCTION:\n"
                "Return ONE valid JSON object only. No markdown, no explanations, no trailing commas."
            )
            repaired_raw = await self._generate_structured_text(
                llm_provider=llm_provider,
                prompt=repair_prompt,
                temperature=0.1,
                max_tokens=3000,
                response_format={"type": "json_object"},
            )
            try:
                content = self._parse_json(repaired_raw)
            except ValueError as second_parse_error:
                logger.error(
                    "SRS parse failed after retry for project %s: %s",
                    project_id,
                    second_parse_error,
                )
                raise ValueError(
                    "Failed to parse SRS JSON after retry. Please retry or switch the AI provider/model."
                ) from second_parse_error

        version = await self._next_version(db, project_id)
        draft = SRSDraft(
            project_id=project_id,
            version=version,
            status="draft",
            language=language,
            content=content,
        )
        db.add(draft)
        await db.flush()

        try:
            refined_result = await self.judging_service.judge_and_refine(
                srs_content=content,
                language=language,
                project_id=project_id,
            )

            refined_srs = refined_result.get("refined_srs") if isinstance(refined_result, dict) else None
            if refined_srs:
                draft.status = "refined"
                draft.content = refined_srs
                logger.info("Draft refined for project %s", project_id)

        except Exception as e:
            logger.error("Failed to refine SRS automatically: %s", e)

        await SRSSnapshotCache.set_from_draft(draft)
        return draft

    @staticmethod
    async def _generate_structured_text(
        *,
        llm_provider: Any,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Dict[str, Any] | None = None,
    ) -> str:
        try:
            return await llm_provider.generate_text(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
        except TypeError:
            return await llm_provider.generate_text(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    def export_pdf(self, draft: SRSDraft) -> bytes:
        try:
            return render_srs_pdf_html(draft)
        except Exception as exc:
            raise RuntimeError(
                "SRS PDF rendering failed. Ensure Node.js and Playwright Chromium are available "
                "(run: npx playwright install chromium)."
            ) from exc

    async def _get_project_messages(self, db: AsyncSession, project_id: int) -> List[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _get_project_transcripts(self, db: AsyncSession, project_id: int) -> List[Asset]:
        stmt = (
            select(Asset)
            .where(
                Asset.project_id == project_id,
                Asset.extracted_text.isnot(None),
                Asset.extracted_text != "",
            )
            .order_by(Asset.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _next_version(self, db: AsyncSession, project_id: int) -> int:
        stmt = select(func.max(SRSDraft.version)).where(SRSDraft.project_id == project_id)
        result = await db.execute(stmt)
        current = result.scalar_one_or_none() or 0
        return current + 1

    @staticmethod
    def _format_conversation(messages: List[ChatMessage]) -> str:
        lines = []
        for msg in messages:
            role = msg.role.lower()
            if role == "user":
                prefix = "User"
            elif role == "assistant":
                prefix = "Assistant"
            else:
                prefix = "System"
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)

    @staticmethod
    def _format_transcripts(transcripts: List[Asset]) -> str:
        blocks: List[str] = []
        for idx, asset in enumerate(transcripts, 1):
            title = asset.original_filename or f"Transcript {idx}"
            text = (asset.extracted_text or "").strip()
            if not text:
                continue
            blocks.append(f"[Transcript {idx} - {title}]\n{text}")
        return "\n\n".join(blocks)

    @staticmethod
    def _build_prompt(conversation: str, transcripts: str, language: str) -> str:
        # Truncate with visible markers so the LLM knows content may be cut
        truncated_transcript = transcripts
        truncated_chat = conversation
        if len(transcripts) > 20000:
            truncated_transcript = (
                transcripts[:20000]
                + "\n\n[TRANSCRIPT TRUNCATED — content beyond this point was omitted due to length. "
                "Mark any sections where evidence was insufficient as confidence=low and add a question to the 'questions' array.]"
            )
        if len(conversation) > 8000:
            truncated_chat = conversation[:8000] + "\n\n[CHAT TRUNCATED]"

        evidence_parts = []
        if truncated_transcript.strip():
            evidence_parts.append(f"Interview transcripts:\n{truncated_transcript}")
        if truncated_chat.strip():
            evidence_parts.append(f"Project chat:\n{truncated_chat}")
        evidence = "\n\n".join(evidence_parts)

        if language == "ar":
            return (
                "أنت مهندس متطلبات معتمد بخبرة تزيد عن 20 عامًا في كتابة وثائق SRS الاحترافية.\n\n"
                "## قاعدة التأسيس الحاسمة\n"
                "كل متطلب تكتبه يجب أن يكون مستنِدًا مباشرةً لتصريح صريح أو مُضمَّن بوضوح في النص المقدَّم. "
                "لا تفترض ولا تخترع ولا تُضيف أنماطًا معيارية من مجال التطبيق. "
                "إذا لم يتناول النص منطقةً ما، اتركها فارغة وأضف سؤالاً للعميل في قسم questions.\n\n"
                "## قاعدة الاحتفاظ بالتفاصيل الدقيقة (Micro-Details Retention)\n"
                "يُمنع منعاً باتاً تلخيص أو تجريد المتطلبات. إذا ذكر المستخدم أسماء أنظمة فرعية (مثل POS, HACCP)، أو تكاملات خارجية (مثل Talabat)، أو تفاصيل دقيقة (مثل سجل تجاري، دفاع مدني)، يجب نقلها حرفياً وذكرها بالاسم داخل المتطلبات الوظيفية وغيرها. لا تستخدم عبارات عامة ومبهمة مثل 'دعم المتطلبات القانونية'.\n\n"
                "## تعريف مستوى الثقة\n"
                "- \"high\": ذُكر صراحةً في موضعين أو أكثر من النص.\n"
                "- \"medium\": ذُكر مرة واحدة، أو يُستشفّ بوضوح من تصريحات أخرى.\n"
                "- \"low\": مستنتج من معرفة المجال؛ غير موجود مباشرةً في النص.\n\n"
                "## الأقسام الإلزامية السبعة (استخدم هذه العناوين بالضبط)\n"
                "1. نظرة عامة وأهداف المشروع\n"
                "2. أصحاب المصلحة وأدوار المستخدمين\n"
                "3. المتطلبات الوظيفية\n"
                "4. المتطلبات غير الوظيفية\n"
                "5. قيود النظام\n"
                "6. خارج النطاق\n"
                "7. أسئلة مفتوحة وافتراضات\n\n"
                "## قصص المستخدمين ومعايير القبول\n"
                "لكل ميزة رئيسية مذكورة من قِبل العميل يجب توليد:\n"
                "- قصة مستخدم بصيغة: 'بوصفي [نوع المستخدم]، أريد [الفعل]، حتى أستطيع [الهدف]'.\n"
                "- معيار قبول قابل للقياس بصيغة: 'يُعتبر الشرط محققًا عندما [حالة قابلة للتحقق]'.\n\n"
                "## قواعد صياغة المتطلبات\n"
                "- كل عنصر في sections.items يجب أن يكون متطلبًا ذريًا كاملاً بصيغة: 'يجب أن يوفر النظام...'.\n"
                "- المقاييس تعكس فقط ما ذكره العميل صراحةً. لا تخترع مؤشرات أداء.\n"
                "- الأسئلة يجب أن تكون موجهة للعميل، محددة، وقابلة للإجابة — وليست عامة.\n"
                "- next_steps هي إجراءات مُرتَّبة حسب الأولوية للفريق التطويري.\n"
                "- activity_diagrams يجب أن تحتوي مخطط نشاط لكل نشاط/تدفق رئيسي في المنتج.\n\n"
                "## قواعد الإخراج الصارمة\n"
                "1) أخرج JSON صالح فقط — بدون markdown، بدون نص إضافي.\n"
                "2) لا تضف أقسامًا خارج الأقسام السبعة المحددة.\n"
                "3) إذا كان القسم بدون أدلة من النص، اجعل items قائمة فارغة [] وأضف سؤالاً في questions.\n"
                "4) تنسيق المخرجات:\n"
                '   {"summary": "...", "metrics": [{"label": "...", "value": "..."}], '
                '"sections": [{"title": "نظرة عامة وأهداف المشروع", "confidence": "high|medium|low", "items": ["يجب أن يوفر النظام..."]}], '
                '"user_stories": [{"role": "مسؤول", "action": "إدارة المستخدمين", "goal": "ضمان الأمان", "acceptance_criteria": ["يُعتبر الشرط محققًا عندما يستطيع المسؤول..."]}], '
                '"user_roles": [{"role": "مسؤول النظام", "description": "يدير المستخدمين والصلاحيات", "permissions": ["إضافة مستخدمين", "تعديل الأدوار"]}], '
                '"activity_diagram": ["بداية -> دخول المستخدم -> تحقق النظام -> عرض لوحة التحكم"], '
                '"activity_diagram_mermaid": "flowchart TD\\n  A[بداية] --> B[دخول المستخدم] --> C[تحقق النظام] --> D[عرض لوحة التحكم]", '
                '"activity_diagrams": [{"title": "تدفق تسجيل الدخول", "activity_diagram": ["بداية -> إدخال بيانات -> تحقق -> لوحة التحكم"], "activity_diagram_mermaid": "flowchart TD\\n  A[بداية] --> B[إدخال بيانات] --> C[تحقق] --> D[لوحة التحكم]"}], '
                '"questions": ["..."], "next_steps": ["..."]}\n\n'
                f"مصادر المشروع:\n{evidence}\n\n"
                "الإخراج (JSON فقط):"
            )

        return (
            "You are a certified Requirements Engineer with 20+ years writing professional SRS documents.\n\n"
            "## CRITICAL GROUNDING RULE\n"
            "Every requirement you write MUST be directly traceable to an explicit or strongly implied "
            "statement in the provided transcript. Do NOT assume, invent, or pad with standard industry "
            "patterns. If a domain area was not discussed, leave its section items empty and add a "
            "client-facing question to the 'questions' array flagging the gap.\n\n"
            "## Micro-Details Retention Rule (CRITICAL)\n"
            "It is strictly forbidden to over-summarize or abstract requirements. If the user mentions specific subsystems (e.g., POS, HACCP), third-party integrations (e.g., Talabat), or exact details (e.g., tax card, fire safety), you MUST retain them literally and mention them by their specific names within the requirements. Do not use generic or vague abstractions like 'support legal requirements'.\n\n"
            "## Confidence Level Definition\n"
            "- \"high\": explicitly stated in 2+ distinct places in the transcript.\n"
            "- \"medium\": stated once, or clearly implied by other statements.\n"
            "- \"low\": inferred from general domain knowledge; NOT directly in transcript.\n\n"
            "## Required Sections — use EXACTLY these 7 titles:\n"
            "1. Project Overview & Objectives\n"
            "2. Stakeholders & User Roles\n"
            "3. Functional Requirements\n"
            "4. Non-Functional Requirements\n"
            "5. System Constraints\n"
            "6. Out of Scope\n"
            "7. Open Questions & Assumptions\n\n"
            "## User Stories & Acceptance Criteria\n"
            "For every major feature mentioned by the client, you MUST generate:\n"
            "- A user story in the format: 'As a [user type], I want [action], so that [goal]'.\n"
            "- At least one measurable acceptance criterion: 'The feature is complete when [verifiable condition]'.\n\n"
            "## Requirement Phrasing Rules\n"
            "- Every item in sections.items must be an atomic, complete requirement in 'The system SHALL...' format.\n"
            "- Metrics must reflect ONLY what the client explicitly mentioned. Do not invent KPIs.\n"
            "- Questions must be client-facing, specific, and answerable — not generic.\n"
            "- next_steps must be prioritized action items for the development team.\n"
            "- activity_diagrams must include one activity diagram for each major product activity/flow.\n\n"
            "## Strict Output Rules\n"
            "1) Return valid JSON only — no markdown fences, no preamble.\n"
            "2) Do NOT add sections outside the 7 listed above.\n"
            "3) If a section has no evidence in the transcript, set its items to [] and add a question.\n"
            "4) Output format:\n"
            '   {"summary": "...", "metrics": [{"label": "...", "value": "..."}], '
            '"sections": [{"title": "Project Overview & Objectives", "confidence": "high|medium|low", "items": ["The system SHALL..."]}], '
            '"user_stories": [{"role": "Admin", "action": "manage users", "goal": "ensure security", "acceptance_criteria": ["The feature is complete when the admin can add/remove users and role changes are audit-logged"]}], '
            '"user_roles": [{"role": "System Administrator", "description": "Manages users and permissions", "permissions": ["add users", "edit roles", "view audit log"]}], '
            '"activity_diagram": ["Start -> User signs in -> System validates credentials -> Dashboard"], '
            '"activity_diagram_mermaid": "flowchart TD\\n  A[Start] --> B[User signs in] --> C[System validates credentials] --> D[Dashboard]", '
            '"activity_diagrams": [{"title": "Login Flow", "activity_diagram": ["Start -> Enter credentials -> Validate -> Dashboard"], "activity_diagram_mermaid": "flowchart TD\\n  A[Start] --> B[Enter credentials] --> C[Validate] --> D[Dashboard]"}], '
            '"questions": ["..."], "next_steps": ["..."]}\n\n'
            f"Project sources:\n{evidence}\n\n"
            "Output (JSON only):"
        )

    @staticmethod
    def _quality_gate(transcripts: str, conversation: str) -> None:
        """Raise ValueError if combined content is too thin to produce a meaningful SRS."""
        combined = (transcripts + " " + conversation).strip()
        word_count = len(combined.split())
        if word_count < 80:
            raise ValueError(
                f"Insufficient content for SRS generation: {word_count} words found. "
                "A minimum of 80 words is required across the transcript and chat history. "
                "Please complete more interview turns before generating the SRS."
            )

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        cleaned = (raw or "").strip()
        if not cleaned:
            raise ValueError("Failed to parse SRS JSON: empty response")

        # Remove markdown code fences if present.
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        parsed = SRSService._try_parse_json_clean(cleaned)
        if parsed is None:
            parsed = SRSService._try_decode_embedded_json(cleaned)
        if parsed is None:
            parsed = SRSService._try_literal_eval_fallback(cleaned)
        if parsed is None:
            extracted = SRSService._extract_balanced_json_object(cleaned)
            if extracted:
                parsed = SRSService._try_parse_json_clean(extracted)
                if parsed is None:
                    parsed = SRSService._try_literal_eval_fallback(extracted)

        if not isinstance(parsed, dict):
            raise ValueError("Failed to parse SRS JSON")

        return SRSService._normalize_srs_content(parsed)

    @staticmethod
    def _try_parse_json_clean(cleaned: str) -> Any:
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _try_decode_embedded_json(cleaned: str) -> Any:
        first_brace = cleaned.find("{")
        if first_brace == -1:
            return None

        decoder = json.JSONDecoder()
        try:
            parsed, _ = decoder.raw_decode(cleaned[first_brace:])
            return parsed
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _try_literal_eval_fallback(cleaned: str) -> Any:
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace == -1 or last_brace <= first_brace:
            return None

        candidate = cleaned[first_brace : last_brace + 1]
        try:
            return ast.literal_eval(candidate)
        except (ValueError, SyntaxError):
            return None

    @staticmethod
    def _extract_balanced_json_object(text: str) -> str | None:
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escaped = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]
        return None

    @staticmethod
    def _normalize_srs_content(content: Dict[str, Any]) -> Dict[str, Any]:
        """Guarantee the stored SRS content has the expected top-level shape."""
        summary = content.get("summary")
        if not isinstance(summary, str):
            summary = "" if summary is None else str(summary)

        metrics = content.get("metrics")
        if not isinstance(metrics, list):
            metrics = []

        sections = content.get("sections")
        if not isinstance(sections, list):
            sections = []

        questions = content.get("questions")
        if not isinstance(questions, list):
            questions = []

        activity_diagram = content.get("activity_diagram")
        if not isinstance(activity_diagram, list):
            activity_diagram = []
        activity_diagram = [str(line).strip() for line in activity_diagram if str(line or "").strip()]

        activity_diagram_mermaid = content.get("activity_diagram_mermaid")
        if not isinstance(activity_diagram_mermaid, str):
            activity_diagram_mermaid = ""
        activity_diagram_mermaid = activity_diagram_mermaid.strip()
        if not activity_diagram_mermaid:
            activity_diagram_mermaid = SRSService._build_mermaid_from_flow_lines(activity_diagram)

        activity_diagrams = SRSService._normalize_activity_diagrams(
            content.get("activity_diagrams"),
            fallback_activity_diagram=activity_diagram,
            fallback_mermaid=activity_diagram_mermaid,
        )

        next_steps = content.get("next_steps")
        if not isinstance(next_steps, list):
            next_steps = []

        # Normalize user_stories
        raw_user_stories = content.get("user_stories")
        user_stories: List[Dict[str, Any]] = []
        if isinstance(raw_user_stories, list):
            for story in raw_user_stories:
                if not isinstance(story, dict):
                    continue
                ac = story.get("acceptance_criteria")
                if not isinstance(ac, list):
                    ac = [str(ac).strip()] if ac else []
                else:
                    ac = [str(c).strip() for c in ac if str(c or "").strip()]
                role = str(story.get("role") or "").strip()
                action = str(story.get("action") or "").strip()
                goal = str(story.get("goal") or "").strip()
                if role or action or goal:
                    user_stories.append({
                        "role": role,
                        "action": action,
                        "goal": goal,
                        "acceptance_criteria": ac,
                    })

        # Normalize user_roles
        raw_user_roles = content.get("user_roles")
        user_roles: List[Dict[str, Any]] = []
        if isinstance(raw_user_roles, list):
            for ur in raw_user_roles:
                if not isinstance(ur, dict):
                    continue
                perms = ur.get("permissions")
                if not isinstance(perms, list):
                    perms = []
                else:
                    perms = [str(p).strip() for p in perms if str(p or "").strip()]
                role_name = str(ur.get("role") or "").strip()
                desc = str(ur.get("description") or "").strip()
                if role_name:
                    user_roles.append({
                        "role": role_name,
                        "description": desc,
                        "permissions": perms,
                    })

        return {
            "summary": summary,
            "metrics": metrics,
            "sections": sections,
            "user_stories": user_stories,
            "user_roles": user_roles,
            "activity_diagram": activity_diagram,
            "activity_diagram_mermaid": activity_diagram_mermaid,
            "activity_diagrams": activity_diagrams,
            "questions": questions,
            "next_steps": next_steps,
        }

    @staticmethod
    def _normalize_activity_diagrams(
        value: Any,
        fallback_activity_diagram: List[str],
        fallback_mermaid: str,
    ) -> List[Dict[str, Any]]:
        diagrams: List[Dict[str, Any]] = []

        if isinstance(value, list):
            for idx, raw in enumerate(value):
                normalized = SRSService._normalize_single_activity_diagram(raw, idx)
                if normalized:
                    diagrams.append(normalized)

        if diagrams:
            return diagrams

        if fallback_activity_diagram or fallback_mermaid:
            return [
                {
                    "title": "Main Activity Flow",
                    "activity_diagram": fallback_activity_diagram,
                    "activity_diagram_mermaid": fallback_mermaid,
                }
            ]

        return []

    @staticmethod
    def _normalize_single_activity_diagram(raw: Any, idx: int) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, dict):
            return None

        title = str(raw.get("title") or f"Activity {idx + 1}").strip()

        lines_raw = raw.get("activity_diagram")
        if not isinstance(lines_raw, list):
            lines_raw = []
        lines = [str(line).strip() for line in lines_raw if str(line or "").strip()]

        mermaid = raw.get("activity_diagram_mermaid")
        if not isinstance(mermaid, str):
            mermaid = ""
        mermaid = mermaid.strip()
        if not mermaid:
            mermaid = SRSService._build_mermaid_from_flow_lines(lines)

        if not lines and not mermaid:
            return None

        return {
            "title": title,
            "activity_diagram": lines,
            "activity_diagram_mermaid": mermaid,
        }

    @staticmethod
    def _build_mermaid_from_flow_lines(lines: List[str]) -> str:
        steps: List[str] = []
        for raw_line in lines:
            text = str(raw_line or "").strip()
            if not text:
                continue
            parts = [segment.strip() for segment in text.split("->") if segment.strip()]
            if not parts:
                continue
            for part in parts:
                if part not in steps:
                    steps.append(part)

        if len(steps) < 2:
            return ""

        code_lines = ["flowchart TD"]
        for idx, label in enumerate(steps):
            node = f"N{idx}"
            safe_label = str(label).replace('"', "'")
            code_lines.append(f"  {node}[\"{safe_label}\"]")
        for idx in range(len(steps) - 1):
            code_lines.append(f"  N{idx} --> N{idx + 1}")
        return "\n".join(code_lines)

    @staticmethod
    def _format_dt(value: datetime | None) -> str:
        if not value:
            return ""
        return value.strftime("%Y-%m-%d %H:%M")
