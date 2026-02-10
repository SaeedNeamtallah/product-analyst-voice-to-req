"""
PGVector Provider Implementation.
Uses PostgreSQL with pgvector extension for vector storage.
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.providers.vectordb.interface import VectorDBInterface
from backend.database.models import Chunk, Project
from backend.database.connection import async_session_maker
import logging

logger = logging.getLogger(__name__)


class PGVectorProvider(VectorDBInterface):
    """PostgreSQL pgvector implementation."""
    
    def __init__(self):
        """Initialize PGVector provider."""
        logger.info("PGVector provider initialized")
    
    async def create_collection(
        self,
        collection_name: str,
        dimension: int,
        **kwargs
    ) -> bool:
        """
        Create collection (for pgvector, this is handled by table creation).
        
        Args:
            collection_name: Not used (using chunks table)
            dimension: Vector dimension
            
        Returns:
            True (table already exists from migrations)
        """
        # With pgvector, collections are handled by the chunks table
        # The vector column is already defined in the model
        logger.info(f"Collection '{collection_name}' ready (using chunks table)")
        return True
    
    async def add_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        ids: List[Any],
        metadata: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> bool:
        """
        Add/update vectors in chunks table.
        
        Args:
            collection_name: Project name or identifier
            vectors: List of embeddings
            ids: List of chunk IDs
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        try:
            from sqlalchemy import update as sa_update
            async with async_session_maker() as session:
                for i, (chunk_id, vector) in enumerate(zip(ids, vectors)):
                    await session.execute(
                        sa_update(Chunk)
                        .where(Chunk.id == chunk_id)
                        .values(embedding=vector)
                    )
                    if (i + 1) % 500 == 0:
                        await session.flush()
                await session.commit()
                logger.info(f"Added {len(vectors)} vectors to collection '{collection_name}'")
                return True
                
        except Exception as e:
            logger.error(f"Error adding vectors: {str(e)}")
            raise
    
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Tuple[Any, float, Dict[str, Any]]]:
        """
        Search for similar vectors.
        Falls back to Python-based similarity if pgvector is not available.
        """
        try:
            async with async_session_maker() as session:
                # Build query to get all relevant chunks
                # We fetch the embedding to calculate similarity in Python
                query = select(
                    Chunk.id,
                    Chunk.content,
                    Chunk.extra_metadata,
                    Chunk.asset_id,
                    Chunk.embedding
                ).where(
                    Chunk.embedding.isnot(None)
                )
                
                # Apply filters
                if filter_dict:
                    if 'project_id' in filter_dict:
                        query = query.where(Chunk.project_id == filter_dict['project_id'])
                    if 'asset_id' in filter_dict:
                        query = query.where(Chunk.asset_id == filter_dict['asset_id'])
                
                result = await session.execute(query)
                rows = result.all()

                if not rows:
                    return []

                # Vectorised cosine similarity via numpy (offloaded to thread)
                import numpy as np
                import asyncio as _aio

                row_ids = [r.id for r in rows]
                row_contents = [r.content for r in rows]
                row_metas = [r.extra_metadata for r in rows]
                row_assets = [r.asset_id for r in rows]
                row_vecs = [r.embedding for r in rows]

                def _rank():
                    q = np.asarray(query_vector, dtype=np.float32)
                    m = np.asarray(row_vecs, dtype=np.float32)
                    dots = m @ q
                    norms = np.linalg.norm(m, axis=1) * np.linalg.norm(q)
                    norms[norms == 0] = 1.0
                    sims = dots / norms
                    k = min(top_k, len(sims))
                    top_idx = np.argpartition(sims, -k)[-k:]
                    top_idx = top_idx[np.argsort(sims[top_idx])[::-1]]
                    return [(int(i), float(sims[i])) for i in top_idx]

                ranked = await _aio.to_thread(_rank)

                results = [
                    (
                        row_ids[i],
                        score,
                        {
                            'content': row_contents[i],
                            'metadata': row_metas[i],
                            'asset_id': row_assets[i],
                        }
                    )
                    for i, score in ranked
                ]

                logger.info(f"Found {len(results)} similar chunks (numpy cosine)")
                return results
                
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise
    
    async def delete_collection(
        self,
        collection_name: str,
        **kwargs
    ) -> bool:
        """
        Delete all chunks for a project.
        
        Args:
            collection_name: Project ID or identifier
            
        Returns:
            True if successful
        """
        try:
            async with async_session_maker() as session:
                project_id = kwargs.get('project_id')
                if project_id:
                    stmt = delete(Chunk).where(Chunk.project_id == project_id)
                    await session.execute(stmt)
                    await session.commit()
                    logger.info(f"Deleted collection '{collection_name}'")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise
    
    async def collection_exists(
        self,
        collection_name: str,
        **kwargs
    ) -> bool:
        """
        Check if project exists.
        
        Args:
            collection_name: Project name
            
        Returns:
            True if exists
        """
        try:
            async with async_session_maker() as session:
                project_id = kwargs.get('project_id')
                if project_id:
                    stmt = select(Project).where(Project.id == project_id)
                    result = await session.execute(stmt)
                    return result.scalar_one_or_none() is not None
                return False
                
        except Exception as e:
            logger.error(f"Error checking collection: {str(e)}")
            return False
