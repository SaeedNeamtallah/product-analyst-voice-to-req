"""
Cohere Embedding Provider Implementation.
Uses Cohere SDK for embeddings.
"""
from typing import List, Optional
import asyncio
import logging
import random
import cohere
from backend.providers.llm.interface import LLMInterface
from backend.config import settings

logger = logging.getLogger(__name__)


class CohereProvider(LLMInterface):
    """Cohere provider implementation (embeddings only)."""

    def __init__(self, api_key: str = None, embed_model: str = None):
        self.api_key = api_key or getattr(settings, "cohere_api_key", "")
        self.embed_model = embed_model or getattr(settings, "cohere_embed_model", "embed-multilingual-v3.0")
        self.client = cohere.Client(self.api_key)
        logger.info(f"Cohere provider initialized with embedding model: {self.embed_model}")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        raise NotImplementedError("CohereProvider does not support text generation in this project.")

    async def generate_embeddings(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        try:
            if not texts:
                return []

            batch_size = kwargs.get("batch_size")
            max_batch_tokens = kwargs.get("max_batch_tokens")
            max_retries = kwargs.get("max_retries", getattr(settings, "cohere_max_retries", 3))
            base_delay = kwargs.get("base_delay", getattr(settings, "cohere_base_retry_delay", 2.0))

            token_cap = getattr(settings, "cohere_max_batch_tokens", 50000)
            if max_batch_tokens is not None:
                token_cap = min(token_cap, int(max_batch_tokens))

            batches = self._build_batches(
                texts=texts,
                batch_size=batch_size,
                max_batch_tokens=token_cap
            )

            embeddings: List[List[float]] = []
            for idx, batch in enumerate(batches):
                if idx > 0:
                    # Throttle between batches to avoid rate limits
                    await asyncio.sleep(1.0 + random.uniform(0, 0.5))
                response = await self._embed_with_retry(
                    texts=batch,
                    max_retries=max_retries,
                    base_delay=base_delay
                )
                embeddings.extend(response.embeddings)

            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings with Cohere: {str(e)}")
            raise

    def get_model_name(self) -> str:
        return self.embed_model

    def get_embedding_dimension(self) -> int:
        model = (self.embed_model or "").lower()
        if "v3" in model:
            return 1024
        return 768

    def _build_batches(
        self,
        texts: List[str],
        batch_size: Optional[int],
        max_batch_tokens: Optional[int]
    ) -> List[List[str]]:
        if not texts:
            return []

        resolved_batch_size = max(1, int(batch_size)) if batch_size else len(texts)
        token_budget = max(1, int(max_batch_tokens)) if max_batch_tokens else None

        batches: List[List[str]] = []
        current_batch: List[str] = []
        current_tokens = 0

        for text in texts:
            estimated_tokens = max(1, len(text) // 4)

            would_exceed_count = len(current_batch) >= resolved_batch_size
            would_exceed_tokens = token_budget is not None and (current_tokens + estimated_tokens) > token_budget

            if current_batch and (would_exceed_count or would_exceed_tokens):
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            current_batch.append(text)
            current_tokens += estimated_tokens

        if current_batch:
            batches.append(current_batch)

        return batches

    async def _embed_with_retry(
        self,
        texts: List[str],
        max_retries: int,
        base_delay: float
    ) -> "cohere.types.EmbedResponse":
        attempt = 0
        while True:
            try:
                return self.client.embed(
                    texts=texts,
                    model=self.embed_model,
                    input_type="search_document"
                )
            except cohere.errors.too_many_requests_error.TooManyRequestsError as e:
                attempt += 1
                if attempt > max_retries:
                    raise

                # Exponential backoff + jitter to avoid thundering herd
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1.5)
                delay = min(delay, 120)  # Cap at 2 minutes
                logger.warning(
                    "Cohere rate limited, retrying in %.2fs (attempt %s/%s)",
                    delay,
                    attempt,
                    max_retries
                )
                await asyncio.sleep(delay)
            except Exception:
                raise
