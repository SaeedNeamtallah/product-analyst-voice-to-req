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

from backend.database.models import ChatMessage, SRSDraft
from backend.providers.llm.factory import LLMProviderFactory
from backend.services.judging_service import JudgingService

logger = logging.getLogger(__name__)


class SRSService:
    """Generate and export SRS drafts from project chat messages."""
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
        if not messages:
            raise ValueError("No chat messages found for this project")

        conversation = self._format_conversation(messages)
        prompt = self._build_prompt(conversation, language)

        llm_provider = LLMProviderFactory.create_provider()
        raw = await llm_provider.generate_text(
            prompt=prompt,
            temperature=0.3,
            max_tokens=3000,
        )
        content = self._parse_json(raw)

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
        """        
        Refactor: 2026-02-15 - Adel Sobhy SRS REFINING
        This is the implementation of the SRS refinement service.
        """
        try:
            refined_result = await self.judging_service.judge_and_refine(
                srs_content=content,
                language=language,
                store_refined=False,  
                db=None,
                project_id=None,
            )

            refined_version = version + 1

            # Update the initial draft in-place with refined content
            draft.version = refined_version
            draft.status = "refined"
            draft.content = refined_result["refined_srs"]


            await db.commit()
            logger.info(f"Draft refined and updated in DB as version {refined_version} for project {project_id}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to refine SRS automatically: {e}")

        await db.refresh(draft)  
        return draft

    def export_pdf(self, draft: SRSDraft) -> bytes:
        content = draft.content or {}
        is_ar = (draft.language == "ar")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)

        # ── Register Unicode font ──
        import os
        font_registered = False
        for font_path in [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]:
            if os.path.isfile(font_path):
                pdf.add_font("UniFont", "", font_path, uni=True)
                pdf.add_font("UniFont", "B", font_path, uni=True)
                font_registered = True
                break
        fn = "UniFont" if font_registered else "Helvetica"

        # ── Color palette ──
        BRAND = (232, 93, 42)     # accent orange
        DARK = (33, 37, 41)       # near-black
        MUTED = (108, 117, 125)   # grey
        LIGHT_BG = (248, 249, 250) # light grey fill
        WHITE = (255, 255, 255)

        def safe(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                return json.dumps(value, ensure_ascii=False)
            return str(value)

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

        # ================================================================
        # PAGE 1 — TITLE PAGE
        # ================================================================
        pdf.add_page()

        # Brand header bar
        pdf.set_fill_color(*BRAND)
        pdf.rect(0, 0, pdf.w, 44, "F")
        pdf.set_y(10)
        pdf.set_font(fn, "B", 22)
        pdf.set_text_color(*WHITE)
        pdf.cell(0, 10, "RAGMind", align="C", ln=True)
        pdf.set_font(fn, "", 11)
        pdf.cell(0, 7, "AI-Powered Requirements Analyst", align="C", ln=True)

        # Main title
        pdf.set_y(60)
        pdf.set_font(fn, "B", 24)
        pdf.set_text_color(*DARK)
        title_text = "Software Requirements Specification" if not is_ar else "مواصفات متطلبات البرمجيات"
        pdf.cell(0, 12, title_text, align="C", ln=True)

        # Subtitle line
        pdf.ln(3)
        pdf.set_draw_color(*BRAND)
        mid = pdf.w / 2
        pdf.line(mid - 30, pdf.get_y(), mid + 30, pdf.get_y())
        pdf.ln(8)

        # Meta info table
        meta_labels = [
            ("Project ID" if not is_ar else "رقم المشروع", str(draft.project_id)),
            ("Version" if not is_ar else "الإصدار", f"v{draft.version}"),
            ("Language" if not is_ar else "اللغة", "Arabic" if is_ar else "English"),
            ("Status" if not is_ar else "الحالة", safe(draft.status).capitalize()),
            ("Generated" if not is_ar else "تاريخ الإنشاء", self._format_dt(draft.created_at)),
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

        # Footer note on title page
        pdf.set_y(250)
        pdf.set_font(fn, "", 8)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 5, "Generated by RAGMind  |  https://ragmind.app", align="C", ln=True)

        # ================================================================
        # PAGE 2+ — CONTENT
        # ================================================================
        pdf.add_page()
        section_num = 0

        # ── 1. Executive Summary ──
        summary = content.get("summary") or ""
        if summary:
            section_num += 1
            section_heading(section_num, "Executive Summary" if not is_ar else "الملخص التنفيذي")
            # Summary in a light-grey box
            pdf.set_fill_color(*LIGHT_BG)
            pdf.set_x(pdf.l_margin)
            y_before = pdf.get_y()
            reset_body()
            pdf.set_font(fn, "", 10)
            text = safe(summary)
            if text.strip():
                pdf.set_x(pdf.l_margin + 4)
                w = pdf.w - pdf.l_margin - pdf.r_margin - 8
                pdf.multi_cell(w, 5.5, text, fill=True)
            pdf.ln(3)
            draw_separator()

        # ── 2. Key Metrics ──
        metrics = content.get("metrics") or []
        if isinstance(metrics, list) and metrics:
            section_num += 1
            section_heading(section_num, "Key Metrics" if not is_ar else "المقاييس الرئيسية")
            col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / 2
            pdf.set_x(pdf.l_margin)
            # Table header
            pdf.set_fill_color(*BRAND)
            pdf.set_text_color(*WHITE)
            pdf.set_font(fn, "B", 10)
            pdf.cell(col_w, 7, "Metric" if not is_ar else "المقياس", border=1, fill=True)
            pdf.cell(col_w, 7, "Value" if not is_ar else "القيمة", border=1, fill=True, ln=True)
            # Table rows
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

        # ── 3+. Requirement Sections ──
        sections = content.get("sections") or []
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_num += 1
            title = safe(section.get("title", "Section"))
            confidence = safe(section.get("confidence", ""))

            heading_text = title
            if confidence:
                heading_text = f"{title}  [{confidence}]"
            section_heading(section_num, heading_text)

            items = section.get("items", [])
            if not isinstance(items, list):
                items = [items]
            for item in items:
                bullet_item(item)
            pdf.ln(1)
            draw_separator()

        # ── Open Questions ──
        questions = content.get("questions") or []
        if not isinstance(questions, list):
            questions = [questions]
        questions = [q for q in questions if safe(q).strip()]
        if questions:
            section_num += 1
            section_heading(section_num, "Open Questions" if not is_ar else "أسئلة مفتوحة")
            for item in questions:
                bullet_item(item)
            pdf.ln(1)
            draw_separator()

        # ── Next Steps ──
        next_steps = content.get("next_steps") or []
        if not isinstance(next_steps, list):
            next_steps = [next_steps]
        next_steps = [s for s in next_steps if safe(s).strip()]
        if next_steps:
            section_num += 1
            section_heading(section_num, "Next Steps" if not is_ar else "الخطوات التالية")
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

        # ── Page numbers on all pages (except title) ──
        total = pdf.page
        for page_num in range(2, total + 1):
            pdf.page = page_num
            pdf.set_y(-15)
            pdf.set_font(fn, "", 8)
            pdf.set_text_color(*MUTED)
            pdf.cell(0, 5, f"Page {page_num - 1} of {total - 1}", align="C")

        return bytes(pdf.output())

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
            prefix = "User" if role == "user" else "Assistant" if role == "assistant" else "System"
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)

    @staticmethod
    def _build_prompt(conversation: str, language: str) -> str:
        if language == "ar":
            return (
                "أنت محلل أعمال محترف. حلّل المحادثة التالية وأنشئ مسودة SRS بنظام JSON فقط.\n"
                "قواعد مهمة:\n"
                "1) أخرج JSON فقط بدون نص إضافي.\n"
                "2) استخدم المفاتيح التالية: summary, metrics, sections, questions, next_steps.\n"
                "3) metrics: قائمة عناصر {label, value}.\n"
                "4) sections: قائمة {title, confidence, items}.\n"
                "5) questions و next_steps قوائم نصية.\n\n"
                "المحادثة:\n"
                f"{conversation}\n\n"
                "الإخراج (JSON فقط):"
            )

        return (
            "You are a senior business analyst. Read the conversation and produce an SRS draft as JSON only.\n"
            "Rules:\n"
            "1) Output JSON only, no extra text.\n"
            "2) Use keys: summary, metrics, sections, questions, next_steps.\n"
            "3) metrics is a list of {label, value}.\n"
            "4) sections is a list of {title, confidence, items}.\n"
            "5) questions and next_steps are string arrays.\n\n"
            "Conversation:\n"
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
    def _format_dt(value: datetime | None) -> str:
        if not value:
            return ""
        return value.strftime("%Y-%m-%d %H:%M")
