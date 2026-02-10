"""
Embedding Service.
Handles generating embeddings using LLM provider.
"""
from typing import List, Callable, Awaitable, Optional
from backend.providers.llm.factory import LLMProviderFactory
from backend.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings."""
    
    def __init__(self):
        """Initialize embedding service with LLM provider."""
        self.llm_provider = LLMProviderFactory.create_embedding_provider()
        logger.info(f"Embedding service initialized with {self.llm_provider.get_model_name()}")
    
    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = None,
        on_batch: Optional[Callable[[int, int], Awaitable[None]]] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for list of texts.
        
        Args:
            texts: List of text strings
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        try:
            if not texts:
                return []
            
            effective_batch = batch_size or settings.embedding_batch_size
            # Cohere trial keys have strict rate limits; cap concurrency to 1
            provider_name = getattr(self.llm_provider, 'embed_model', '') or ''
            is_cohere = hasattr(self.llm_provider, 'client') and isinstance(
                getattr(self.llm_provider, 'client', None), type(None)
            ) is False and 'cohere' in type(self.llm_provider).__module__
            default_concurrency = 1 if is_cohere else max(1, int(getattr(settings, "embedding_concurrency", 2)))
            concurrency = default_concurrency
            total_texts = len(texts)

            batches = [
                texts[i:i + effective_batch]
                for i in range(0, total_texts, effective_batch)
            ]

            semaphore = asyncio.Semaphore(concurrency)
            lock = asyncio.Lock()
            processed = 0

            async def run_batch(batch: List[str]) -> List[List[float]]:
                nonlocal processed
                async with semaphore:
                    result = await self.llm_provider.generate_embeddings(
                        texts=batch,
                        batch_size=len(batch),
                        max_batch_tokens=settings.voyage_max_batch_tokens
                    )
                if on_batch:
                    async with lock:
                        processed += len(batch)
                        try:
                            await on_batch(processed, total_texts)
                        except Exception:
                            pass
                return result

            results = await asyncio.gather(*[run_batch(batch) for batch in batches])
            embeddings = [item for batch in results for item in batch]
            
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    async def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for single text.
        
        Args:
            text: Text string
            
        Returns:
            Embedding vector
        """
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else []
    
    def get_embedding_dimension(self) -> int:
        """
        Get the embedding vector dimension.
        
        Returns:
            Dimension size
        """
        return self.llm_provider.get_embedding_dimension()
