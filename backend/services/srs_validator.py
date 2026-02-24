from __future__ import annotations

import re
from typing import Any, Dict, List


class SRSValidator:
    """Validates SRS JSON against strict professional IEEE-like rules."""

    EXPECTED_TOP_LEVEL_KEYS = {"summary", "metrics", "sections", "questions", "next_steps"}
    EXPECTED_SECTIONS = [
        "Introduction",
        "Overall Description",
        "Functional Requirements",
        "Non-Functional Requirements",
        "External Interface Requirements",
        "Data Requirements",
        "Assumptions & Dependencies",
        "Constraints",
        "Requirements Diagrams (Mermaid)",
    ]

    @classmethod
    def validate(cls, content: Dict[str, Any]) -> List[str]:
        """
        Validate an SRS JSON dict.
        Returns a list of error messages; an empty list means the content is valid.
        """
        errors: List[str] = []

        if not isinstance(content, dict):
            return ["Root object must be a JSON dictionary."]

        # 1. Top-level keys ────────────────────────────────────────────────
        actual_keys = set(content.keys())
        missing     = cls.EXPECTED_TOP_LEVEL_KEYS - actual_keys
        extra       = actual_keys - cls.EXPECTED_TOP_LEVEL_KEYS
        if missing:
            errors.append(f"Missing required top-level keys: {missing}")
        if extra:
            errors.append(
                f"Invalid extra top-level keys: {extra}. "
                f"Only {cls.EXPECTED_TOP_LEVEL_KEYS} are allowed."
            )

        # 2. metrics ───────────────────────────────────────────────────────
        metrics = content.get("metrics")
        if metrics is not None:
            if not isinstance(metrics, list):
                errors.append("'metrics' must be a list.")
            else:
                for idx, m in enumerate(metrics):
                    if not isinstance(m, dict) or "label" not in m or "value" not in m:
                        errors.append(
                            f"Metric at index {idx} must be a dict with 'label' and 'value'."
                        )

        # 3. sections ──────────────────────────────────────────────────────
        sections = content.get("sections")
        if not isinstance(sections, list):
            errors.append("'sections' must be a list of dictionaries.")
            return errors   # fatal – stop here

        actual_titles: List[str] = []
        for idx, sec in enumerate(sections):
            if not isinstance(sec, dict):
                errors.append(f"Section at index {idx} must be a dictionary.")
                continue
            title = sec.get("title", "")
            actual_titles.append(title)
            if "items" not in sec or not isinstance(sec["items"], list):
                errors.append(f"Section '{title}' must contain an 'items' list.")

        for expected in cls.EXPECTED_SECTIONS:
            if expected not in actual_titles:
                errors.append(f"Missing mandatory section: '{expected}'.")

        # 4. Functional Requirements ───────────────────────────────────────
        fr_section = next(
            (s for s in sections if isinstance(s, dict) and s.get("title") == "Functional Requirements"),
            None,
        )
        if fr_section:
            items    = fr_section.get("items", [])
            has_fr   = any(re.match(r"^FR-\d+", str(item))   for item in items)
            has_ac   = any(re.match(r"^AC-FR-\d+", str(item)) for item in items)
            has_shall = any("shall" in str(item).lower()      for item in items)
            if items and not has_fr:
                errors.append("Functional Requirements must include IDs starting with 'FR-'.")
            if items and not has_ac:
                errors.append("Functional Requirements must include Acceptance Criteria starting with 'AC-FR-'.")
            if items and not has_shall:
                errors.append("Functional Requirements must use the word 'shall'.")

        # 5. Non-Functional Requirements ───────────────────────────────────
        nfr_section = next(
            (s for s in sections if isinstance(s, dict) and s.get("title") == "Non-Functional Requirements"),
            None,
        )
        if nfr_section:
            items   = nfr_section.get("items", [])
            has_nfr = any(re.match(r"^NFR-\d+", str(item)) for item in items)
            if items and not has_nfr:
                errors.append("Non-Functional Requirements must include IDs starting with 'NFR-'.")

        # 6. Mermaid diagrams ──────────────────────────────────────────────
        mermaid_section = next(
            (s for s in sections if isinstance(s, dict) and s.get("title") == "Requirements Diagrams (Mermaid)"),
            None,
        )
        if mermaid_section:
            items         = mermaid_section.get("items", [])
            mermaid_count = sum(1 for item in items if str(item).strip().startswith("```mermaid"))
            if mermaid_count < 3:
                errors.append(
                    f"'Requirements Diagrams (Mermaid)' must contain at least 3 fenced mermaid "
                    f"code blocks. Found {mermaid_count}."
                )

        return errors