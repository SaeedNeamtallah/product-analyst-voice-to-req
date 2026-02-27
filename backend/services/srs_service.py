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

from backend.database.models import ChatMessage, SRSDraft
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
        # Fetch the latest live patch draft which contains our incrementally built summaries
        latest_draft = await self.get_latest_draft(db, project_id)
        if not latest_draft or not isinstance(latest_draft.content, dict):
            raise ValueError("No live patch draft found. Cannot generate final SRS. Please complete interview steps first.")
        
        draft_summary = latest_draft.content.get("summary", {})
        if not draft_summary:
            raise ValueError("Live patch draft has no summary data. Cannot generate final SRS.")
            
        llm_provider = LLMProviderFactory.create_provider()
        
        # 1. Generate Core Sections (Overview, Scope, Features, Constraints)
        core_prompt = self._build_core_prompt(draft_summary, language)
        core_raw = await self._generate_structured_text(
            llm_provider=llm_provider,
            prompt=core_prompt,
            temperature=0.2,
            max_tokens=2500,
            response_format={"type": "json_object"},
        )
        core_content = self._parse_json(core_raw)
        
        # 2. Generate User Roles and Stories
        users_prompt = self._build_users_prompt(draft_summary, language)
        users_raw = await self._generate_structured_text(
            llm_provider=llm_provider,
            prompt=users_prompt,
            temperature=0.2,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        users_content = self._parse_json(users_raw)
        
        # 3. Generate Activity Diagrams
        flow_prompt = self._build_flow_prompt(draft_summary, language)
        flow_raw = await self._generate_structured_text(
            llm_provider=llm_provider,
            prompt=flow_prompt,
            temperature=0.1,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        flow_content = self._parse_json(flow_raw)
        
        # Merge all partial contents safely
        merged_content = self._normalize_srs_content({
            "metrics": core_content.get("metrics", []),
            "sections": core_content.get("sections", []),
            "questions": core_content.get("questions", []),
            "next_steps": core_content.get("next_steps", []),
            "summary": "Generated incrementally from live patches.",
            "user_roles": users_content.get("user_roles", []),
            "user_stories": users_content.get("user_stories", []),
            "activity_diagrams": flow_content.get("activity_diagrams", []),
        })

        version = await self._next_version(db, project_id)
        draft = SRSDraft(
            project_id=project_id,
            version=version,
            status="draft",
            language=language,
            content=merged_content,
        )
        db.add(draft)
        await db.flush()

        try:
            refined_result = await self.judging_service.judge_and_refine(
                srs_content=merged_content,
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
    def _build_core_prompt(summary: Dict[str, Any], language: str) -> str:
        evidence = json.dumps(summary, ensure_ascii=False, indent=2)
        if language == "ar":
            return (
                "أنت مهندس متطلبات معتمد بخبرة تزيد عن 20 عامًا.\n"
                "قم بإنشاء الأقسام الأساسية بناءً على هذا الملخص التراكمي فقط.\n"
                "## قاعدة التأسيس\nلا تضف أي متطلبات من خارج الملخص. احتفظ بالتفاصيل الدقيقة وأسماء الأنظمة.\n"
                "## الأقسام المطلوبة\n"
                "1. نظرة عامة وأهداف المشروع\n2. المتطلبات الوظيفية\n3. المتطلبات غير الوظيفية\n4. قيود النظام\n5. خارج النطاق\n6. أسئلة مفتوحة وافتراضات\n\n"
                "الإخراج JSON فقط بالصيغة التالية:\n"
                '{"metrics": [], "sections": [{"title": "...", "confidence": "high", "items": ["يجب أن..."]}], "questions": [], "next_steps": []}\n\n'
                f"الملخص:\n{evidence}"
            )
        return (
            "You are a certified Requirements Engineer with 20+ years of experience.\n"
            "Generate the core sections based ONLY on this cumulative summary.\n"
            "## Grounding Rule\nDo not invent requirements. Keep micro-details and specific system names.\n"
            "## Required Sections\n"
            "1. Project Overview & Objectives\n2. Functional Requirements\n3. Non-Functional Requirements\n4. System Constraints\n5. Out of Scope\n6. Open Questions & Assumptions\n\n"
            "Output JSON only in this format:\n"
            '{"metrics": [], "sections": [{"title": "...", "confidence": "high", "items": ["The system SHALL..."]}], "questions": [], "next_steps": []}\n\n'
            f"Summary:\n{evidence}"
        )

    @staticmethod
    def _build_users_prompt(summary: Dict[str, Any], language: str) -> str:
        evidence = json.dumps(summary, ensure_ascii=False, indent=2)
        if language == "ar":
            return (
                "الرجاء استخراج أدوار المستخدمين وقصص المستخدمين من الملخص التالي.\n"
                "الإخراج JSON فقط بالصيغة التالية:\n"
                '{"user_roles": [{"role": "...", "description": "...", "permissions": ["..."]}], '
                '"user_stories": [{"role": "...", "action": "...", "goal": "...", "acceptance_criteria": ["..."]}]}\n\n'
                f"الملخص:\n{evidence}"
            )
        return (
            "Extract User Roles and User Stories based ONLY on the following summary.\n"
            "Output JSON only in this format:\n"
            '{"user_roles": [{"role": "...", "description": "...", "permissions": ["..."]}], '
            '"user_stories": [{"role": "...", "action": "...", "goal": "...", "acceptance_criteria": ["..."]}]}\n\n'
            f"Summary:\n{evidence}"
        )

    @staticmethod
    def _build_flow_prompt(summary: Dict[str, Any], language: str) -> str:
        evidence = json.dumps(summary, ensure_ascii=False, indent=2)
        if language == "ar":
            return (
                "قم بإنشاء مسارات العمل (Activity Diagrams) بناءً على الملخص التالي.\n"
                "الإخراج JSON فقط بالصيغة التالية:\n"
                '{"activity_diagrams": [{"title": "...", "activity_diagram": ["بداية -> خطوة 1 -> نهاية"], '
                '"activity_diagram_mermaid": "flowchart TD\\n  A[بداية] --> B[خطوة 1] --> C[نهاية]"}]}\n\n'
                f"الملخص:\n{evidence}"
            )
        return (
            "Generate Activity Diagrams based ONLY on the following summary.\n"
            "Output JSON only in this format:\n"
            '{"activity_diagrams": [{"title": "...", "activity_diagram": ["Start -> Step 1 -> End"], '
            '"activity_diagram_mermaid": "flowchart TD\\n  A[Start] --> B[Step 1] --> C[End]"}]}\n\n'
            f"Summary:\n{evidence}"
        )

    @staticmethod
    def _quality_gate(conversation: str) -> None:
        """Raise ValueError if combined content is too thin to produce a meaningful SRS."""
        combined = conversation.strip()
        word_count = len(combined.split())
        if word_count < 80:
            raise ValueError(
                f"Insufficient content for SRS generation: {word_count} words found. "
                "A minimum of 80 words is required across the chat history. "
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
