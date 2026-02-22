"""
Query Service.
Handles query processing over raw extracted transcripts.
"""
from typing import List, Dict, Any, Optional
from backend.database.connection import async_session_maker
from backend.database.models import Asset
from sqlalchemy import select
import logging
import re

logger = logging.getLogger(__name__)


class QueryService:
    """Service for processing queries against stored transcripts."""
    
    def __init__(self):
        """Initialize query service."""
        logger.info("Query service initialized")
    
    async def search_similar_chunks(
        self,
        query: str,
        project_id: int,
        top_k: int = 5,
        asset_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search project transcripts and return top matching transcript blocks.
        
        Args:
            query: Search query
            project_id: Project ID to search within
            top_k: Number of results to return
            asset_id: Optional asset ID to filter by
            
        Returns:
            List of transcript snippets with metadata
        """
        try:
            async with async_session_maker() as session:
                stmt = select(
                    Asset.id,
                    Asset.original_filename,
                    Asset.extracted_text,
                ).where(
                    Asset.project_id == project_id,
                    Asset.status == "completed",
                    Asset.extracted_text.isnot(None),
                    Asset.extracted_text != "",
                )
                if asset_id is not None:
                    stmt = stmt.where(Asset.id == asset_id)
                rows = (await session.execute(stmt)).all()

            if not rows:
                logger.info("No transcripts found for query")
                return []

            query_tokens = self._tokenize(query)
            scored_results: List[Dict[str, Any]] = []
            for row in rows:
                transcript = row.extracted_text or ""
                score = self._lexical_score(query_tokens, transcript)
                if score <= 0:
                    continue

                snippet = transcript[:4000]
                scored_results.append({
                    'chunk_id': row.id,
                    'similarity': score,
                    'content': snippet,
                    'metadata': {
                        'document_name': row.original_filename,
                        'chunk_index': 0,
                    },
                    'asset_id': row.id,
                })

            scored_results.sort(key=lambda x: x['similarity'], reverse=True)
            final_results = scored_results[:top_k]
            logger.info(f"Found {len(final_results)} transcript matches for query")
            return final_results
            
        except Exception as e:
            logger.error(f"Error searching transcripts: {str(e)}")
            raise

    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        tokens = re.findall(r"\w+", text.lower())
        return [t for t in tokens if len(t) > 1]

    def _lexical_score(self, query_tokens: List[str], text: str) -> float:
        if not query_tokens or not text:
            return 0.0
        text_tokens = set(self._tokenize(text))
        if not text_tokens:
            return 0.0
        overlap = sum(1 for token in query_tokens if token in text_tokens)
        return overlap / max(len(query_tokens), 1)
