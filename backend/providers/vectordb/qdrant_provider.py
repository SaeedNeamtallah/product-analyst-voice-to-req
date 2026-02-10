"""
Qdrant Provider Implementation.
Uses Qdrant standalone vector database.
"""
from typing import List, Dict, Any, Optional, Tuple
from backend.providers.vectordb.interface import VectorDBInterface
from backend.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class QdrantProvider(VectorDBInterface):
    """
    Qdrant vector database implementation.
    Optional provider - requires Qdrant server running.
    """
    
    def __init__(self, url: str = "http://localhost:6333", api_key: str = ""):
        """
        Initialize Qdrant provider.
        
        Args:
            url: Qdrant server URL
            api_key: Optional API key
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            
            if url.startswith("path://"):
                path = url.replace("path://", "")
                self.client = QdrantClient(path=path)
                logger.info(f"Qdrant provider initialized with local path: {path}")
            else:
                self.client = QdrantClient(
                    url=url,
                    api_key=api_key if api_key else None,
                    timeout=60,
                    prefer_grpc=False,
                )
                logger.info(f"Qdrant provider initialized at {url}")
        except ImportError:
            logger.error("qdrant-client not installed. Install with: pip install qdrant-client")
            raise
    
    async def create_collection(
        self,
        collection_name: str,
        dimension: int,
        **kwargs
    ) -> bool:
        """
        Create Qdrant collection.
        
        Args:
            collection_name: Collection name
            dimension: Vector dimension
            
        Returns:
            True if successful
        """
        try:
            from qdrant_client.models import Distance, VectorParams

            # Check if collection exists
            result = await asyncio.to_thread(self.client.get_collections)
            collections = result.collections
            exists = any(c.name == collection_name for c in collections)
            
            if not exists:
                await asyncio.to_thread(
                    self.client.create_collection,
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=dimension,
                        distance=Distance.COSINE
                    )
                )
                # Create payload indexes for faster filtered search
                try:
                    from qdrant_client.models import PayloadSchemaType
                    for field in ("project_id", "asset_id"):
                        await asyncio.to_thread(
                            self.client.create_payload_index,
                            collection_name=collection_name,
                            field_name=field,
                            field_schema=PayloadSchemaType.INTEGER,
                        )
                except Exception as idx_err:
                    logger.warning(f"Could not create payload index: {idx_err}")
                logger.info(f"Created Qdrant collection '{collection_name}'")
            else:
                logger.info(f"Qdrant collection '{collection_name}' already exists")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            raise
    
    async def add_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        ids: List[Any],
        metadata: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> bool:
        """
        Add vectors to Qdrant collection.
        
        Args:
            collection_name: Collection name
            vectors: List of embeddings
            ids: List of IDs
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        try:
            if vectors:
                exists = await self.collection_exists(collection_name)
                if not exists:
                    await self.create_collection(collection_name, dimension=len(vectors[0]))

            from qdrant_client.models import PointStruct

            points = []
            for i, (point_id, vector) in enumerate(zip(ids, vectors)):
                payload = metadata[i] if metadata and i < len(metadata) else {}
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                )
            
            batch_size = max(1, int(settings.qdrant_upsert_batch_size))
            for start in range(0, len(points), batch_size):
                batch = points[start:start + batch_size]
                for attempt in range(3):
                    try:
                        await asyncio.to_thread(
                            self.client.upsert,
                            collection_name=collection_name,
                            points=batch
                        )
                        break
                    except Exception as e:
                        if attempt == 2:
                            raise
                        logger.warning(
                            "Qdrant upsert failed, retrying batch %s-%s (%s)",
                            start,
                            start + len(batch) - 1,
                            str(e)
                        )
                        await asyncio.sleep(0.5 * (attempt + 1))
            
            logger.info(f"Added {len(points)} points to Qdrant collection '{collection_name}'")
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
        Search Qdrant for similar vectors.
        
        Args:
            collection_name: Collection name
            query_vector: Query embedding
            top_k: Number of results
            filter_dict: Optional filters
            
        Returns:
            List of (id, score, payload)
        """
        try:
            # Build filter if provided
            search_filter = None
            if filter_dict:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                conditions = []
                for key, value in filter_dict.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                search_filter = Filter(must=conditions)
            
            # Search
            payload_fields = ["content", "metadata", "asset_id", "project_id"]

            if hasattr(self.client, "query_points"):
                search_result = await asyncio.to_thread(
                    lambda: self.client.query_points(
                        collection_name=collection_name,
                        query=query_vector,
                        limit=top_k,
                        query_filter=search_filter,
                        with_payload=payload_fields
                    )
                )
            elif hasattr(self.client, "search_points"):
                search_result = await asyncio.to_thread(
                    lambda: self.client.search_points(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        limit=top_k,
                        query_filter=search_filter,
                        with_payload=payload_fields
                    )
                )
            elif hasattr(self.client, "search"):
                search_result = await asyncio.to_thread(
                    lambda: self.client.search(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        limit=top_k,
                        query_filter=search_filter,
                        with_payload=payload_fields
                    )
                )
            else:
                raise AttributeError("Qdrant client does not support query/search")
            
            # Format results
            results = []
            hits = getattr(search_result, "points", search_result)
            for hit in hits:
                results.append((
                    hit.id,
                    hit.score,
                    hit.payload
                ))
            
            logger.info(f"Found {len(results)} similar points in Qdrant")
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
        Delete Qdrant collection.
        
        Args:
            collection_name: Collection name
            
        Returns:
            True if successful
        """
        try:
            await asyncio.to_thread(self.client.delete_collection, collection_name=collection_name)
            logger.info(f"Deleted Qdrant collection '{collection_name}'")
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
        Check if Qdrant collection exists.
        
        Args:
            collection_name: Collection name
            
        Returns:
            True if exists
        """
        try:
            result = await asyncio.to_thread(self.client.get_collections)
            return any(c.name == collection_name for c in result.collections)
            
        except Exception as e:
            logger.error(f"Error checking collection: {str(e)}")
            return False
