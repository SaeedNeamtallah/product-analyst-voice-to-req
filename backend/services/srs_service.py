"""
    SRS draft generation and export service.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import ChatMessage, SRSDraft, Project
from backend.providers.llm.factory import LLMProviderFactory
from backend.services.judging_service import JudgingService
from backend.services.interview_service import InterviewService
from backend.services.srs_validator import SRSValidator

logger = logging.getLogger(__name__)


class SRSService:
    """Generate and export SRS drafts from project chat messages."""

    def __init__(self):
        self.judging_service = JudgingService()
        self.interview_service = InterviewService()

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
        # ── 1. Fetch interview summary ──────────────────────────────────────
        interview_result = await self.interview_service.get_next_question(db, project_id, language)
        interview_summary = interview_result.get("summary")   # renamed to avoid clash
        if not interview_summary:
            raise ValueError("No summary found for this project")

        # ── 2. Build prompt from recent Q&A ────────────────────────────────
        recent_messages = await self._get_recent_qa_messages(db, project_id, limit=10)
        qa_context = self._format_conversation(recent_messages)

        prompt = self._build_prompt(
            conversation=qa_context,
            summary_data=interview_summary,
            language=language,
        )

        # ── 3. LLM generation with up to 2 repair retries ──────────────────
        llm_provider = LLMProviderFactory.create_provider()
        content: Dict[str, Any] | None = None
        last_errors: List[str] = []
        max_retries = 2

        for attempt in range(max_retries + 1):
            raw = await llm_provider.generate_text(
                prompt=prompt,
                temperature=0.3,
                max_tokens=6000,
            )
            try:
                parsed = self._parse_json(raw)
                parsed = self._normalize_content(parsed)   # coerce malformed fields before validation
            except ValueError as exc:
                logger.warning("Attempt %d – JSON parse failed: %s", attempt, exc)
                if attempt == max_retries:
                    raise ValueError(
                        f"SRS LLM output could not be parsed as JSON after {max_retries + 1} attempts."
                    ) from exc
                continue

            validation_errors = SRSValidator.validate(parsed)
            if not validation_errors:
                content = parsed
                break

            last_errors = validation_errors
            logger.warning(
                "Attempt %d – SRS validation failed (%d errors): %s",
                attempt,
                len(validation_errors),
                validation_errors[:3],
            )

            if attempt < max_retries:
                # Build a repair prompt that includes the error list
                repair_note = (
                    "The previous output had the following validation errors. Fix ALL of them:\n"
                    + "\n".join(f"- {e}" for e in validation_errors)
                    + "\n\nOriginal output:\n"
                    + raw
                )
                prompt = self._build_prompt(
                    conversation=qa_context,
                    summary_data=interview_summary,
                    language=language,
                    repair_note=repair_note,
                )

        if content is None:
            raise ValueError(
                f"SRS could not be generated after {max_retries + 1} attempts. "
                f"Last validation errors: {last_errors}"
            )

        # ── 4. Judge & refine the raw SRS ──────────────────────────────────
        try:
            judged = await self.judging_service.judge_and_refine(
                srs_content=content,
                language=language,
                project_id=project_id,
            )
            refined = judged.get("refined_srs")
            # Normalize before validating refined output
            if refined and isinstance(refined, dict):
                refined = self._normalize_content(refined)
            if refined and not SRSValidator.validate(refined):
                content = refined
            else:
                logger.warning(
                    "Refined SRS failed validation – keeping original generated content."
                )
        except Exception as exc:
            logger.warning("Judging/refinement failed (non-fatal): %s", exc)

        # ── 5. Persist SRSDraft to DB ───────────────────────────────────────
        version = await self._next_version(db, project_id)
        draft = SRSDraft(
            project_id=project_id,
            version=version,
            content=content,
            language=language,
            status="draft",
        )
        db.add(draft)
        await db.flush()   # flush so draft.id is populated before PDF export

        # ── 6. Build PDF ────────────────────────────────────────────────────
        pdf_bytes = self._build_pdf(content=content, project_id=project_id, language=language)

        # Store PDF bytes on the draft if the model has a pdf_bytes column,
        # otherwise callers can retrieve via export_pdf().
        if hasattr(draft, "pdf_bytes"):
            draft.pdf_bytes = pdf_bytes
            await db.flush()

        return draft

    # ──────────────────────────────────────────────────────────────────────
    # PDF builder (extracted so generate_draft stays readable)
    # ──────────────────────────────────────────────────────────────────────

    def _build_pdf(
        self,
        content: Dict[str, Any],
        project_id: int,
        language: str,
    ) -> bytes:
        pdf = FPDF()
        fn = "Arial"
        is_ar = language == "ar"

        # ── Color palette ──────────────────────────────────────────────────
        BRAND    = (232, 93,  42)
        DARK     = (33,  37,  41)
        MUTED    = (108, 117, 125)
        LIGHT_BG = (248, 249, 250)
        WHITE    = (255, 255, 255)

        def safe(value: Any) -> str:
            """Convert any value to a latin-1-safe string for FPDF core fonts."""
            if value is None:
                return ""
            if isinstance(value, dict):
                text = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, str):
                text = str(value)
            else:
                text = value
            return SRSService._sanitize_text(text)

        def reset_body():
            pdf.set_text_color(*DARK)
            pdf.set_font(fn, "", 10)
            pdf.set_x(pdf.l_margin)

        def draw_separator():
            y = pdf.get_y() + 2
            pdf.set_draw_color(*MUTED)
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.set_y(y + 4)

        def section_heading(number: int, title: str):
            pdf.ln(4)
            pdf.set_x(pdf.l_margin)
            pdf.set_font(fn, "B", 13)
            pdf.set_text_color(*BRAND)
            pdf.cell(0, 8, f"{number}.  {title}", ln=True)
            pdf.set_text_color(*DARK)
            pdf.ln(1)

        def bullet_item(text: str, indent: float = 6):
            text = safe(text)
            if not text.strip():
                return
            pdf.set_x(pdf.l_margin + indent)
            pdf.set_font(fn, "", 10)
            pdf.set_text_color(*DARK)
            w = pdf.w - pdf.l_margin - pdf.r_margin - indent
            pdf.multi_cell(w, 5.5, f"  {text}")
            pdf.ln(0.5)

        # ── PAGE 1 — TITLE PAGE ────────────────────────────────────────────
        pdf.add_page()
        pdf.set_fill_color(*BRAND)
        pdf.rect(0, 0, pdf.w, 44, "F")
        pdf.set_y(10)
        pdf.set_font(fn, "B", 22)
        pdf.set_text_color(*WHITE)
        pdf.cell(0, 10, "RAGMind", align="C", ln=True)
        pdf.set_font(fn, "", 11)
        pdf.cell(0, 7, "AI-Powered Requirements Analyst", align="C", ln=True)

        pdf.set_y(60)
        pdf.set_font(fn, "B", 24)
        pdf.set_text_color(*DARK)
        title_text = (
            "مواصفات متطلبات البرمجيات" if is_ar
            else "Software Requirements Specification"
        )
        pdf.cell(0, 12, title_text, align="C", ln=True)

        pdf.ln(3)
        pdf.set_draw_color(*BRAND)
        mid = pdf.w / 2
        pdf.line(mid - 30, pdf.get_y(), mid + 30, pdf.get_y())
        pdf.ln(8)

        now = datetime.now()
        meta_labels = [
            ("رقم المشروع"  if is_ar else "Project ID",   str(project_id)),
            ("الإصدار"      if is_ar else "Version",       "v1"),
            ("اللغة"        if is_ar else "Language",      "Arabic" if is_ar else "English"),
            ("الحالة"       if is_ar else "Status",        "Draft"),
            ("تاريخ الإنشاء" if is_ar else "Generated",   self._format_dt(now)),
        ]
        table_w = 100
        table_x = (pdf.w - table_w) / 2
        for label, value in meta_labels:
            pdf.set_x(table_x)
            pdf.set_font(fn, "B", 10)
            pdf.set_text_color(*MUTED)
            pdf.cell(50, 7, label, border=0)
            pdf.set_font(fn, "", 10)
            pdf.set_text_color(*DARK)
            pdf.cell(50, 7, value, border=0, ln=True)

        pdf.set_y(250)
        pdf.set_font(fn, "", 8)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 5, "Generated by RAGMind  |  https://ragmind.app", align="C", ln=True)

        # ── PAGE 2+ — CONTENT ──────────────────────────────────────────────
        pdf.add_page()
        section_num = 0

        # 1. Executive Summary
        srs_summary = content.get("summary") or ""   # use srs_summary to avoid name clash
        if srs_summary:
            section_num += 1
            section_heading(section_num, "الملخص التنفيذي" if is_ar else "Executive Summary")
            pdf.set_fill_color(*LIGHT_BG)
            pdf.set_x(pdf.l_margin)
            reset_body()
            text = safe(srs_summary)
            if text.strip():
                pdf.set_x(pdf.l_margin + 4)
                w = pdf.w - pdf.l_margin - pdf.r_margin - 8
                pdf.multi_cell(w, 5.5, text, fill=True)
            pdf.ln(3)
            draw_separator()

        # 2. Key Metrics
        metrics = content.get("metrics") or []
        if isinstance(metrics, list) and metrics:
            section_num += 1
            section_heading(section_num, "المقاييس الرئيسية" if is_ar else "Key Metrics")
            col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / 2
            pdf.set_x(pdf.l_margin)
            pdf.set_fill_color(*BRAND)
            pdf.set_text_color(*WHITE)
            pdf.set_font(fn, "B", 10)
            pdf.cell(col_w, 7, "المقياس" if is_ar else "Metric", border=1, fill=True)
            pdf.cell(col_w, 7, "القيمة" if is_ar else "Value",   border=1, fill=True, ln=True)
            pdf.set_text_color(*DARK)
            for i, m in enumerate(metrics):
                if not isinstance(m, dict):
                    continue
                bg = LIGHT_BG if i % 2 == 0 else WHITE
                pdf.set_fill_color(*bg)
                pdf.set_x(pdf.l_margin)
                pdf.set_font(fn, "B", 10)
                pdf.cell(col_w, 7, safe(m.get("label", "")), border=1, fill=True)
                pdf.set_font(fn, "", 10)
                pdf.cell(col_w, 7, safe(m.get("value", "")), border=1, fill=True, ln=True)
            pdf.ln(3)
            draw_separator()

        # 3+. Requirement sections (with Mermaid rendering)
        import tempfile
        import subprocess
        import os
        try:
            from cairosvg import svg2png
            _CAIROSVG_AVAILABLE = True
        except ImportError:
            _CAIROSVG_AVAILABLE = False

        sections = content.get("sections") or []
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_num += 1
            title      = safe(section.get("title", "Section"))
            confidence = safe(section.get("confidence", ""))
            heading_text = f"{title}  [{confidence}]" if confidence else title
            section_heading(section_num, heading_text)

            items = section.get("items", [])
            # coerce non-list items into a single-item list for uniform processing
            if not isinstance(items, list):
                items = [items]

            for item in items:
                text = safe(item)
                # look for a fenced mermaid code block
                if text.strip().startswith("```mermaid") and text.strip().endswith("```"):
                    mermaid_code = text.strip()[len("```mermaid"):-3].strip()
                    rendered = False
                    if _CAIROSVG_AVAILABLE:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            mmd_path = os.path.join(tmpdir, "diagram.mmd")
                            svg_path = os.path.join(tmpdir, "diagram.svg")
                            png_path = os.path.join(tmpdir, "diagram.png")
                            with open(mmd_path, "w", encoding="utf-8") as f:
                                f.write(mermaid_code)
                            try:
                                subprocess.run(
                                    ["mmdc", "-i", mmd_path, "-o", svg_path],
                                    check=True, capture_output=True,
                                )
                                svg2png(url=svg_path, write_to=png_path)
                                pdf.image(png_path, w=pdf.w - pdf.l_margin - pdf.r_margin)
                                rendered = True
                            except Exception as exc:
                                logger.warning("Mermaid render failed: %s", exc)
                    if not rendered:
                        bullet_item("[Mermaid diagram failed to render]")
                else:
                    bullet_item(text)

            pdf.ln(1)
            draw_separator()

        # Open Questions
        questions = content.get("questions") or []
        if not isinstance(questions, list):
            questions = [questions]
        questions = [q for q in questions if safe(q).strip()]
        if questions:
            section_num += 1
            section_heading(section_num, "أسئلة مفتوحة" if is_ar else "Open Questions")
            for item in questions:
                bullet_item(item)
            pdf.ln(1)
            draw_separator()

        # Next Steps
        next_steps = content.get("next_steps") or []
        if not isinstance(next_steps, list):
            next_steps = [next_steps]
        next_steps = [s for s in next_steps if safe(s).strip()]
        if next_steps:
            section_num += 1
            section_heading(section_num, "الخطوات التالية" if is_ar else "Next Steps")
            for idx, item in enumerate(next_steps, 1):
                text = safe(item)
                if text.strip():
                    pdf.set_x(pdf.l_margin + 6)
                    pdf.set_font(fn, "B", 10)
                    pdf.set_text_color(*BRAND)
                    pdf.cell(8, 5.5, f"{idx}.")
                    pdf.set_font(fn, "", 10)
                    pdf.set_text_color(*DARK)
                    w = pdf.w - pdf.l_margin - pdf.r_margin - 14
                    pdf.multi_cell(w, 5.5, text)
                    pdf.ln(0.5)

        # Page numbers (skip title page)
        total = pdf.page
        for page_num in range(2, total + 1):
            pdf.page = page_num
            pdf.set_y(-15)
            pdf.set_font(fn, "", 8)
            pdf.set_text_color(*MUTED)
            pdf.cell(0, 5, f"Page {page_num - 1} of {total - 1}", align="C")

        return bytes(pdf.output())


    async def export_pdf(self, db: AsyncSession, project_id: int) -> bytes:
        """
        Return PDF bytes for the latest SRS draft of the given project.
        Raises ValueError if no draft exists yet.
        """
        draft = await self.get_latest_draft(db, project_id)
        if draft is None:
            raise ValueError(f"No SRS draft found for project {project_id}. Generate one first.")
        content = draft.content if isinstance(draft.content, dict) else {}
        return self._build_pdf(
            content=content,
            project_id=project_id,
            language=str(draft.language or "ar"),
        )

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """
        Replace characters that FPDF core fonts (latin-1) cannot encode.

        Covers the most common LLM-output offenders:
          - Unicode quotes/apostrophes  → straight equivalents
          - Em-dash / en-dash           → hyphen
          - Ellipsis character          → three dots
          - Non-breaking space          → regular space
          - Arabic / other non-latin-1  → transliterated or dropped

        Falls back to encoding with 'replace' for anything not in the table.
        """
        replacements = {
            '‘': "'",   # left single quotation mark
            '’': "'",   # right single quotation mark / apostrophe
            '“': '"',   # left double quotation mark
            '”': '"',   # right double quotation mark
            '–': '-',   # en-dash
            '—': '-',   # em-dash  ← THE character that caused the crash
            '…': '...', # horizontal ellipsis
            ' ': ' ',   # non-breaking space
            '·': '*',   # middle dot
            '•': '*',   # bullet
            '‣': '>',   # triangular bullet
            '▪': '*',   # small black square
            '→': '->',  # rightwards arrow
            '←': '<-',  # leftwards arrow
            '×': 'x',   # multiplication sign
            '÷': '/',   # division sign
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        # Final safety net: drop anything still outside latin-1
        return text.encode('latin-1', errors='replace').decode('latin-1')

    # ──────────────────────────────────────────────────────────────────────
    # DB helpers
    # ──────────────────────────────────────────────────────────────────────

    async def _get_recent_qa_messages(
        self, db: AsyncSession, project_id: int, limit: int = 10
    ) -> List[ChatMessage]:
        """Return the most recent `limit` user/assistant messages in chronological order."""
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.project_id == project_id,
                ChatMessage.role.in_(["user", "assistant"]),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def _next_version(self, db: AsyncSession, project_id: int) -> int:
        stmt = select(func.max(SRSDraft.version)).where(SRSDraft.project_id == project_id)
        result = await db.execute(stmt)
        current = result.scalar_one_or_none() or 0
        return current + 1

    # ──────────────────────────────────────────────────────────────────────
    # Static helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _format_conversation(messages: List[ChatMessage]) -> str:
        lines = []
        for msg in messages:
            role   = msg.role.lower()
            prefix = "User" if role == "user" else "Assistant" if role == "assistant" else "System"
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)

    @staticmethod
    def _build_prompt(
        conversation: str,
        summary_data: Dict[str, Any],
        language: str,
        repair_note: str | None = None,
    ) -> str:
        summary_text = (
            json.dumps(summary_data, ensure_ascii=False, indent=2)
            if summary_data else "{}"
        )

        common_rules = (
            "A) JSON OUTPUT RULES:\n"
            "- Output VALID JSON ONLY. No markdown wrappers, no conversational text.\n"
            "- Use ONLY these exact top-level keys: summary, metrics, sections, questions, next_steps.\n"
            "- 'sections' must be a list of {title, confidence, items}.\n\n"

            "B) MANDATORY SECTION ORDER (IEEE-like):\n"
            "Your 'sections' array MUST include exactly these titles in this order:\n"
            "1. Introduction\n"
            "2. Overall Description\n"
            "3. Functional Requirements\n"
            "4. Non-Functional Requirements\n"
            "5. External Interface Requirements\n"
            "6. Data Requirements\n"
            "7. Assumptions & Dependencies\n"
            "8. Constraints\n"
            "9. Requirements Diagrams (Mermaid)\n\n"

            "C) REQUIREMENT WRITING RULES:\n"
            "- Under 'Functional Requirements', items MUST use IDs and 'shall'. "
            "Example: 'FR-1: The system shall...'\n"
            "- Each FR MUST be immediately followed by Acceptance Criteria as separate items. "
            "Example: 'AC-FR-1.1: Given... When... Then...'\n"
            "- Under 'Non-Functional Requirements', items MUST use IDs and measurable constraints. "
            "Example: 'NFR-1 (Performance): The system shall <metric>'\n"
            "- Avoid vague words (e.g. fast, secure) unless quantified.\n\n"

            "D) MERMAID DIAGRAM RULES:\n"
            "- Under 'Requirements Diagrams (Mermaid)', you MUST provide at least 3 diagram items.\n"
            "- Each item MUST be a plain string starting exactly with ```mermaid and ending with ```.\n"
            "- Required diagrams:\n"
            "  1. System Context Diagram (flowchart LR)\n"
            "  2. Main Use Cases Diagram (flowchart TD)\n"
            "  3. Requirements Traceability Diagram (flowchart TD mapping Feature -> FR -> NFR)\n"
        )

        repair_block = ""
        if repair_note:
            repair_block = f"\n\n⚠️ REPAIR REQUIRED:\n{repair_note}\n"

        if language == "ar":
            return (
                "أنت محلل أعمال محترف. حلّل الملخص التراكمي والمحادثة الأخيرة وأنشئ مسودة SRS بنظام JSON بالتوافق مع IEEE.\n\n"
                f"{common_rules}\n"
                "اكتب محتوى الأقسام (باستثناء الأكواد والمفاتيح) باللغة العربية.\n"
                "تأكد من تطبيق جميع القواعد بصرامة تامة.\n"
                f"{repair_block}\n"
                f"الملخص التراكمي:\n{summary_text}\n\n"
                "المحادثة الأخيرة:\n"
                f"{conversation}\n\n"
                "الإخراج (JSON فقط):"
            )

        return (
            "You are a senior business analyst. Read the cumulative summary and the recent conversation, "
            "and produce a strict IEEE-like SRS draft as JSON only.\n\n"
            f"{common_rules}\n"
            "Ensure ALL rules are strictly applied. "
            "Failure to include IDs, specific metrics, or valid Mermaid blocks will result in rejection.\n"
            f"{repair_block}\n"
            f"Cumulative Summary:\n{summary_text}\n\n"
            "Recent Conversation:\n"
            f"{conversation}\n\n"
            "Output (JSON only):"
        )

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", raw)
            if not match:
                raise ValueError("Failed to parse SRS JSON")
            return json.loads(match.group(0))

    @staticmethod
    def _normalize_content(content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coerce common LLM mis-shapings so they don't cause unnecessary retries.

        Known patterns fixed here:
        - metrics is None / missing  → []
        - metrics is a dict          → convert to [{label, value}, ...] list
        - metrics items lack label/value keys → wrap as {label: key, value: val}
        - questions / next_steps is a str or None → wrap in list
        - sections items is None     → []
        """
        if not isinstance(content, dict):
            return content

        # ── metrics ──────────────────────────────────────────────────────
        metrics = content.get("metrics")
        if metrics is None:
            content["metrics"] = []
        elif isinstance(metrics, dict):
            # e.g. {"Users": "500", "Uptime": "99.9%"}
            content["metrics"] = [
                {"label": str(k), "value": str(v)}
                for k, v in metrics.items()
            ]
        elif isinstance(metrics, list):
            fixed = []
            for item in metrics:
                if isinstance(item, dict):
                    # ensure both keys exist
                    if "label" not in item or "value" not in item:
                        # try common alternatives
                        label = item.get("label") or item.get("name") or item.get("metric") or str(item)
                        value = item.get("value") or item.get("val") or ""
                        fixed.append({"label": str(label), "value": str(value)})
                    else:
                        fixed.append(item)
                elif isinstance(item, str):
                    # e.g. "Response time: < 200ms"
                    if ":" in item:
                        label, _, value = item.partition(":")
                    else:
                        label, value = item, ""
                    fixed.append({"label": label.strip(), "value": value.strip()})
            content["metrics"] = fixed

        # ── questions ────────────────────────────────────────────────────
        questions = content.get("questions")
        if questions is None:
            content["questions"] = []
        elif isinstance(questions, str):
            content["questions"] = [questions] if questions.strip() else []

        # ── next_steps ───────────────────────────────────────────────────
        next_steps = content.get("next_steps")
        if next_steps is None:
            content["next_steps"] = []
        elif isinstance(next_steps, str):
            content["next_steps"] = [next_steps] if next_steps.strip() else []

        # ── sections items ───────────────────────────────────────────────
        sections = content.get("sections")
        if isinstance(sections, list):
            for sec in sections:
                if isinstance(sec, dict) and sec.get("items") is None:
                    sec["items"] = []
                if isinstance(sec, dict) and not isinstance(sec.get("items"), list):
                    raw_items = sec.get("items")
                    sec["items"] = [raw_items] if raw_items else []

        return content

    @staticmethod
    def _format_dt(value: datetime | None) -> str:
        if not value:
            return ""
        return value.strftime("%Y-%m-%d %H:%M")