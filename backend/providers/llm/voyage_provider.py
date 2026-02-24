"""
Voyage AI Embedding Provider Implementation.
Uses voyageai SDK for embeddings.
"""
from typing import List, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from backend.providers.llm.interface import LLMInterface
from backend.config import settings

logger = logging.getLogger(__name__)


class VoyageProvider(LLMInterface):
    """Voyage AI provider implementation (embeddings only)."""

    def __init__(self, api_key: str = None, embed_model: str = None, output_dimension: int = None):
        self.api_key = api_key or getattr(settings, "voyage_api_key", "")
        self.embed_model = embed_model or getattr(settings, "voyage_embed_model", "voyage-3-large")
        self.output_dimension = output_dimension or getattr(settings, "voyage_output_dimension", 1024)

        try:
            import voyageai
        except ImportError as exc:
            raise ImportError("voyageai is not installed. Install with: pip install voyageai") from exc

        self.client = voyageai.Client(api_key=self.api_key)
        self._executor = ThreadPoolExecutor(max_workers=4)
        logger.info(f"Voyage provider initialized with embedding model: {self.embed_model}")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        raise NotImplementedError("VoyageProvider does not support text generation in this project.")

    async def generate_embeddings(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        try:
            if not texts:
                return []

            batch_size = int(kwargs.get("batch_size") or 10)
            max_batch_tokens = int(kwargs.get("max_batch_tokens") or 120000)
            safe_limit = int(max_batch_tokens * 0.9)

            def estimate_tokens(text: str) -> int:
                # Rough heuristic: ~4 chars per token for English-like text.
                return max(1, len(text) // 4)

            def truncate_to_limit(text: str) -> str:
                max_chars = max_batch_tokens * 4
                if len(text) <= max_chars:
                    return text
                logger.warning("Truncating text to fit Voyage batch token limit")
                return text[:max_chars]

            batches: List[List[str]] = []
            current_batch: List[str] = []
            current_tokens = 0

            for text in texts:
                safe_text = truncate_to_limit(text)
                token_est = estimate_tokens(safe_text)

                if current_batch and (
                    len(current_batch) >= batch_size or current_tokens + token_est > safe_limit
                ):
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = 0

                current_batch.append(safe_text)
                current_tokens += token_est

            if current_batch:
                batches.append(current_batch)

            loop = asyncio.get_event_loop()
            results: List[List[float]] = []
            for batch in batches:
                response = await loop.run_in_executor(
                    self._executor,
                    lambda b=batch: self.client.embed(
                        texts=b,
                        model=self.embed_model,
                        input_type="document",
                        output_dimension=self.output_dimension
                    )
                )
                results.extend(response.embeddings)

            return results
        except Exception as e:
            logger.error(f"Error generating embeddings with Voyage: {str(e)}")
            raise

    def get_model_name(self) -> str:
        return self.embed_model

    def get_embedding_dimension(self) -> int:
        model_name = (self.embed_model or "").lower()
        if self.output_dimension:
            return int(self.output_dimension)
        if "voyage-3" in model_name:
            return 1024
        return 1024
