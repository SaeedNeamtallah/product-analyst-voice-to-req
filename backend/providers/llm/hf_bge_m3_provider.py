"""
Hugging Face BGE-M3 Embedding Provider (local).
Uses sentence-transformers for embeddings.
"""
from typing import List, Optional
import logging
import asyncio

from backend.providers.llm.interface import LLMInterface
from backend.config import settings

logger = logging.getLogger(__name__)


class BgeM3Provider(LLMInterface):
    """Local BGE-M3 provider implementation (embeddings only)."""

    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or settings.hf_embedding_model
        self.device = device

        try:
            from sentence_transformers import SentenceTransformer
            import torch
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers/torch not installed. Install with: pip install sentence-transformers torch"
            ) from exc

        if self.device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = SentenceTransformer(self.model_name, device=self.device)
        logger.info(f"BGE-M3 provider initialized with model: {self.model_name} on {self.device}")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        raise NotImplementedError("BgeM3Provider does not support text generation in this project.")

    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 16,
        **kwargs
    ) -> List[List[float]]:
        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(
                    texts,
                    batch_size=batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings with BGE-M3: {str(e)}")
            raise

    def get_model_name(self) -> str:
        return self.model_name

    def get_embedding_dimension(self) -> int:
        return int(self.model.get_sentence_embedding_dimension())
