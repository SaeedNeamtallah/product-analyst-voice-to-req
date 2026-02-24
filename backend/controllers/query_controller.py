"""
Query Controller.
Business logic for query processing and answer generation.
"""
from typing import Dict, Any, Optional, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import logging

from backend.database.models import Project
from backend.services.srs_snapshot_cache import SRSSnapshotCache

logger = logging.getLogger(__name__)


class QueryController:
    """Controller for query operations."""
    
    def __init__(self):
        """Initialize query controller."""
        from backend.services.answer_service import AnswerService

        self.answer_service = AnswerService()
    
    async def answer_query(
        self,
        db: AsyncSession,
        project_id: int,
        query: str,
        top_k: int = 5,
        language: str = "ar",
        asset_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process query and generate answer.
        
        Args:
            db: Database session
            project_id: Project ID to search in
            query: User question
            top_k: Number of transcript matches to retrieve
            language: Response language ('ar' or 'en')
            asset_id: Optional specific transcript document to search
            
        Returns:
            Dictionary with answer and metadata
        """
        try:
            logger.info(f"Processing query for project {project_id}: {query[:50]}...")
            project_context = await self._get_project_context(db=db, project_id=project_id)

            result = await self.answer_service.generate_answer_no_context(
                query=query,
                language=language,
                project_context=project_context,
            )
            logger.info("Generated answer for query in context-window mode (no RAG)")
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise

    async def answer_query_stream(
        self,
        db: AsyncSession,
        project_id: int,
        query: str,
        top_k: int = 5,
        language: str = "ar",
        asset_id: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream SSE events: first the sources, then token-by-token answer,
        then a [DONE] sentinel.
        """
        try:
            logger.info(
                f"Processing streaming query for project {project_id}: {query[:50]}..."
            )
            project_context = await self._get_project_context(db=db, project_id=project_id)

            yield f"data: {json.dumps({'type': 'sources', 'sources': [], 'context_used': 0})}\n\n"
            async for token in self.answer_service.generate_answer_no_context_stream(
                query=query,
                language=language,
                project_context=project_context,
            ):
                yield f"data: {json.dumps({'type': 'token', 'token': token}, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error streaming query: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    @staticmethod
    async def _get_project_context(db: AsyncSession, project_id: int) -> Dict[str, Any]:
        project_stmt = select(Project).where(Project.id == project_id)
        project_result = await db.execute(project_stmt)
        project = project_result.scalar_one_or_none()
        srs_snapshot = await SRSSnapshotCache.get_latest_snapshot(db=db, project_id=project_id)

        context: Dict[str, Any] = {
            "project_id": project_id,
            "project_name": str(project.name) if project and project.name else "",
            "project_description": str(project.description) if project and project.description else "",
            "srs": None,
        }

        if isinstance(srs_snapshot, dict):
            context["srs"] = srs_snapshot

        return context
