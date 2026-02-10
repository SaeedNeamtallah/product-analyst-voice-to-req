"""
Query Service.
Handles query processing and similarity search.
"""
from typing import List, Dict, Any, Optional, Tuple
from backend.services.embedding_service import EmbeddingService
from backend.providers.vectordb.factory import VectorDBProviderFactory
from backend.providers.llm.factory import LLMProviderFactory
from backend.runtime_config import get_runtime_value
from backend.config import settings
from backend.database.connection import async_session_maker
from backend.database.models import Chunk
from sqlalchemy import select
import logging
import re

logger = logging.getLogger(__name__)


class QueryService:
    """Service for processing queries and searching."""
    
    def __init__(self):
        """Initialize query service."""
        self.embedding_service = EmbeddingService()
        self.vector_db = VectorDBProviderFactory.create_provider()
        self.rewrite_provider = LLMProviderFactory.create_provider()
        logger.info("Query service initialized")
    
    async def search_similar_chunks(
        self,
        query: str,
        project_id: int,
        top_k: int = 5,
        asset_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for chunks similar to query.
        
        Args:
            query: Search query
            project_id: Project ID to search within
            top_k: Number of results to return
            asset_id: Optional asset ID to filter by
            
        Returns:
            List of similar chunks with metadata
        """
        try:
            query_text = query
            if get_runtime_value("query_rewrite_enabled", settings.query_rewrite_enabled):
                query_text = await self._rewrite_query(query)

            # Generate query embedding
            query_embedding = await self.embedding_service.generate_single_embedding(query_text)
            
            # Build filter
            filter_dict = {'project_id': project_id}
            if asset_id:
                filter_dict['asset_id'] = asset_id
            
            candidate_k = get_runtime_value("retrieval_candidate_k", settings.retrieval_candidate_k)
            candidate_k = max(int(candidate_k or top_k), top_k)

            # Search vector database
            vector_db = VectorDBProviderFactory.create_provider()
            results = await vector_db.search(
                collection_name=f"project_{project_id}",
                query_vector=query_embedding,
                top_k=candidate_k,
                filter_dict=filter_dict
            )
            
            formatted_results = await self._hydrate_chunk_payloads(results)

            if not formatted_results:
                logger.info("No similar chunks found for query")
                return []

            hybrid_enabled = get_runtime_value("retrieval_hybrid_enabled", settings.retrieval_hybrid_enabled)
            hybrid_alpha = float(get_runtime_value("retrieval_hybrid_alpha", settings.retrieval_hybrid_alpha))
            hybrid_alpha = max(0.0, min(1.0, hybrid_alpha))
            rerank_enabled = get_runtime_value("retrieval_rerank_enabled", settings.retrieval_rerank_enabled)
            rerank_top_k = int(get_runtime_value("retrieval_rerank_top_k", settings.retrieval_rerank_top_k))

            scored_results = formatted_results
            if hybrid_enabled:
                scored_results = self._apply_hybrid_scoring(scored_results, query_text)
                for item in scored_results:
                    item['similarity'] = hybrid_alpha * item['similarity'] + (1.0 - hybrid_alpha) * item['lexical_score']

            if rerank_enabled:
                scored_results = self._apply_rerank(scored_results, query_text, rerank_top_k)

            scored_results.sort(key=lambda x: x['similarity'], reverse=True)
            final_results = scored_results[:top_k]
            logger.info(f"Found {len(final_results)} similar chunks for query")
            return final_results
            
        except Exception as e:
            logger.error(f"Error searching chunks: {str(e)}")
            raise

    async def _hydrate_chunk_payloads(
        self,
        results: List[Tuple[Any, float, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        if not results:
            return []

        chunk_ids = [chunk_id for chunk_id, _, _ in results]
        id_to_score = {chunk_id: score for chunk_id, score, _ in results}

        async with async_session_maker() as session:
            query = (
                select(Chunk.id, Chunk.content, Chunk.extra_metadata, Chunk.asset_id)
                .where(Chunk.id.in_(chunk_ids))
            )
            rows = await session.execute(query)
            rows = rows.all()

        payload_map = {
            row.id: {
                'content': row.content,
                'metadata': row.extra_metadata or {},
                'asset_id': row.asset_id
            }
            for row in rows
        }

        formatted_results = []
        for chunk_id in chunk_ids:
            payload = payload_map.get(chunk_id, {})
            formatted_results.append({
                'chunk_id': chunk_id,
                'similarity': id_to_score.get(chunk_id, 0.0),
                'content': payload.get('content', ''),
                'metadata': payload.get('metadata', {}),
                'asset_id': payload.get('asset_id')
            })

        return formatted_results

    async def _rewrite_query(self, query: str) -> str:
        if not query.strip() or len(query.strip()) < 5:
            return query

        prompt = (
            "Rewrite the user query to improve document retrieval. "
            "Keep the same language and meaning, remove filler words, "
            "and return only the rewritten query.\n\n"
            f"Query: {query}\nRewritten:"
        )

        try:
            rewritten = await self.rewrite_provider.generate_text(
                prompt=prompt,
                temperature=0.2,
                max_tokens=200
            )
            rewritten = rewritten.strip().strip('"')
            return rewritten if rewritten else query
        except Exception:
            return query

    def _apply_hybrid_scoring(
        self,
        results: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        query_tokens = self._tokenize(query)
        for item in results:
            content = item.get('content', '') or ''
            parent_content = (item.get('metadata') or {}).get('parent_content')
            if parent_content:
                content = parent_content
            item['lexical_score'] = self._lexical_score(query_tokens, content)
        return results

    def _apply_rerank(
        self,
        results: List[Dict[str, Any]],
        query: str,
        rerank_top_k: int
    ) -> List[Dict[str, Any]]:
        rerank_count = max(1, min(rerank_top_k, len(results)))
        head = results[:rerank_count]
        tail = results[rerank_count:]
        query_tokens = self._tokenize(query)

        for item in head:
            metadata = item.get('metadata') or {}
            parent_content = metadata.get('parent_content')
            content = parent_content if parent_content else item.get('content', '')
            item['similarity'] = max(item['similarity'], self._lexical_score(query_tokens, content))

        head.sort(key=lambda x: x['similarity'], reverse=True)
        return head + tail

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
