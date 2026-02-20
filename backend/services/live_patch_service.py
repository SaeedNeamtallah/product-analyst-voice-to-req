"""
Live SRS patch builder for all chat flows (not interview-only).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.database.models import ChatMessage
from backend.services.interview_service import InterviewService
from backend.services.constraints_checker import SlotFillingStateMachine

_CHAT_AREA_HINTS = {
    "discovery": {"problem", "goal", "target", "audience", "business", "pain", "مشكلة", "هدف", "جمهور", "قيمة"},
    "scope": {"mvp", "phase", "scope", "out of scope", "in scope", "release", "نطاق", "مرحلة", "خارج النطاق", "اصدار"},
    "users": {"user", "admin", "role", "persona", "permission", "مستخدم", "عميل", "مدير", "صلاحية"},
    "features": {"feature", "module", "screen", "workflow", "report", "dashboard", "ميزة", "شاشة", "تقرير", "لوحة"},
    "constraints": {"budget", "timeline", "deadline", "security", "performance", "stack", "hosting", "ميزانية", "موعد", "أمان", "أداء", "تقنية"},
}


class LivePatchService:
    """Builds cumulative summary/coverage + structured patch events from chat history."""

    @classmethod
    def build_from_messages(
        cls,
        language: str,
        messages: List[ChatMessage],
        last_summary: Dict[str, List[str]] | None,
        last_coverage: Dict[str, float] | None,
    ) -> Dict[str, Any]:
        old_summary = last_summary if isinstance(last_summary, dict) else {}
        old_coverage = last_coverage if isinstance(last_coverage, dict) else {}

        new_summary = cls._build_summary(messages, old_summary)
        new_coverage = cls._build_coverage(new_summary, old_coverage)
        stage = InterviewService._pick_focus_area(new_coverage)

        latest_user = ""
        for msg in reversed(messages):
            if str(msg.role or "").lower() == "user":
                latest_user = str(msg.content or "").strip()
                break

        slot_analysis = SlotFillingStateMachine.analyze(
            language=language,
            latest_user_answer=latest_user,
            last_summary=old_summary,
            last_coverage=old_coverage,
        )

        reflector_signals = InterviewService._reflect_conversation(
            language=language,
            latest_user_answer=latest_user,
            last_summary=old_summary,
            last_coverage=old_coverage,
            slot_analysis=slot_analysis,
        )

        doc_patch = InterviewService._build_documentation_patch(
            language=language,
            stage=stage,
            new_summary=new_summary,
            old_summary=old_summary,
            new_coverage=new_coverage,
            old_coverage=old_coverage,
            reflector_signals=reflector_signals,
        )

        cycle_trace = InterviewService._build_cycle_trace(
            language=language,
            stage=stage,
            reflector_signals=reflector_signals,
            coverage=new_coverage,
            doc_patch=doc_patch,
        )
        topic_navigation = InterviewService._build_topic_navigation(
            language=language,
            summary=new_summary,
            coverage=new_coverage,
            reflector_signals=reflector_signals,
        )

        return {
            "stage": stage,
            "summary": new_summary,
            "coverage": new_coverage,
            "signals": reflector_signals,
            "live_patch": doc_patch,
            "cycle_trace": cycle_trace,
            "topic_navigation": topic_navigation,
        }

    @classmethod
    def _build_summary(
        cls,
        messages: List[ChatMessage],
        last_summary: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        summary = {
            area: list(last_summary.get(area, [])) if isinstance(last_summary.get(area), list) else []
            for area in ["discovery", "scope", "users", "features", "constraints"]
        }

        for message in messages[-28:]:
            role = str(message.role or "").lower()
            if role not in {"user", "assistant"}:
                continue

            content = str(message.content or "").strip()
            if not content:
                continue

            lines = cls._split_content(content)
            for line in lines:
                area = cls._detect_area(line)
                if not InterviewService._contains_similar_requirement(summary[area], line):
                    summary[area].append(line)

        for area in summary:
            summary[area] = summary[area][:18]

        return summary

    @staticmethod
    def _split_content(content: str) -> List[str]:
        clean = re.sub(r"\s+", " ", content).strip()
        chunks = re.split(r"[\n\r]+|[•\-]\s+|[\.\؟\!\;\،]\s+", clean)
        lines: List[str] = []
        for chunk in chunks:
            text = str(chunk or "").strip()
            if len(text) < 10:
                continue
            if len(text) > 220:
                text = text[:220].rstrip() + "…"
            lines.append(text)
        return lines[:10]

    @classmethod
    def _detect_area(cls, line: str) -> str:
        lower = line.lower()
        best_area = "discovery"
        best_score = 0

        for area, hints in _CHAT_AREA_HINTS.items():
            score = sum(1 for token in hints if token in lower)
            if score > best_score:
                best_score = score
                best_area = area

        return best_area

    @staticmethod
    def _build_coverage(
        summary: Dict[str, List[str]],
        last_coverage: Dict[str, float],
    ) -> Dict[str, float]:
        coverage: Dict[str, float] = {}
        for area in ["discovery", "scope", "users", "features", "constraints"]:
            items_count = len(summary.get(area, []))
            estimated = min(100.0, float(items_count * 14))
            prev = float(last_coverage.get(area, 0) or 0)
            coverage[area] = round(max(prev, estimated), 2)
        return coverage
