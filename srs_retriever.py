"""Simple SRS Retriever - Get stored SRS draft from database."""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from sqlalchemy import func, select

from backend.database.connection import async_session_maker
from backend.database.models import Project, SRSDraft


async def get_srs_draft(project_ref: str | int) -> Dict[str, Any] | None:
    """
    Retrieve the latest SRS draft for a project.

    Args:
        project_ref: Project ID (int) or project name (str)

    Returns:
        Dict containing SRS draft data, or None if not found
    """
    async with async_session_maker() as db:
        # Resolve project ID
        if isinstance(project_ref, str) and not project_ref.isdigit():
            stmt = select(Project.id).where(func.lower(Project.name) == project_ref.lower()).limit(1)
            result = await db.execute(stmt)
            project_id = result.scalar_one_or_none()
            if project_id is None:
                return None
        else:
            project_id = int(project_ref)

        # Get latest SRS draft
        stmt = (
            select(SRSDraft)
            .where(SRSDraft.project_id == project_id)
            .order_by(SRSDraft.version.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        draft = result.scalar_one_or_none()

        if draft is None:
            return None

        return {
            "project_id": draft.project_id,
            "version": draft.version,
            "status": draft.status,
            "language": draft.language,
            "created_at": draft.created_at.isoformat() if draft.created_at else None,
            "content": draft.content,
        }


def print_srs_text(draft: Dict[str, Any]) -> None:
    """Print SRS draft in readable text format."""
    if draft is None:
        print("No SRS draft found.")
        return

    content = draft.get("content") or {}
    print("=== SRS DRAFT ===")
    print(f"Project ID: {draft.get('project_id')}")
    print(f"Version: {draft.get('version')}")
    print(f"Status: {draft.get('status')}")
    print(f"Language: {draft.get('language')}")
    print(f"Created: {draft.get('created_at')}")

    if summary := content.get("summary"):
        print(f"\n[Summary]\n{summary}")

    if metrics := content.get("metrics"):
        print("\n[Metrics]")
        for m in metrics:
            if isinstance(m, dict):
                print(f"- {m.get('label', '')}: {m.get('value', '')}")

    if sections := content.get("sections"):
        print("\n[Sections]")
        for s in sections:
            if isinstance(s, dict):
                title = s.get("title", "Section")
                conf = s.get("confidence")
                print(f"\n- {title}" + (f" ({conf})" if conf else ""))
                for item in s.get("items", []):
                    print(f"  • {item}")

    if questions := content.get("questions"):
        print("\n[Open Questions]")
        for q in questions:
            print(f"- {q}")

    if next_steps := content.get("next_steps"):
        print("\n[Next Steps]")
        for i, step in enumerate(next_steps, 1):
            print(f"{i}. {step}")


# Example usage
async def main():
    # Get SRS for project "webfolio"
    draft = await get_srs_draft("webfolio")
    print_srs_text(draft)

    # Or get by ID
    # draft = await get_srs_draft(3)
    # print_srs_text(draft)


if __name__ == "__main__":
    asyncio.run(main())
