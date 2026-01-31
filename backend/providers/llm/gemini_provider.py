"""
Google Gemini 2.5 Flash LLM Provider Implementation.
Uses google-generativeai SDK for text generation and embeddings.
"""
from typing import List, Optional
import google.generativeai as genai
from backend.providers.llm.interface import LLMInterface
from backend.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class GeminiProvider(LLMInterface):
    """Google Gemini LLM provider implementation."""
    
    def __init__(self, api_key: str = None, model_name: str = None):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Gemini API key (defaults to settings)
            model_name: Model name (defaults to settings)
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize models
        self.chat_model = genai.GenerativeModel(self.model_name)
        self.embedding_model = "models/gemini-embedding-001"
        
        logger.info(f"Gemini provider initialized with model: {self.model_name}")
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text using Gemini.
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            
        Returns:
            Generated text
        """
        try:
            # Combine system prompt and user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Configure generation
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 2048,
            )
            
            # Generate response (run in thread pool for async)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.chat_model.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating text with Gemini: {str(e)}")
            raise
    
    async def generate_embeddings(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """
        Generate embeddings using Gemini.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = []
            
            # Use asyncio.gather for parallel processing with a semaphore to control concurrency
            # This is significantly faster than sequential processing
            MAX_CONCURRENT_REQUESTS = 20
            sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
            
            async def embed_single(text):
                async with sem:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: genai.embed_content(
                            model=self.embedding_model,
                            content=text,
                            task_type="retrieval_document"
                        )
                    )
                    return result["embedding"]
            
            # Create tasks
            tasks = [embed_single(text) for text in texts]
            
            # Execute in parallel
            embeddings = await asyncio.gather(*tasks)
            
            return list(embeddings)
            
        except Exception as e:
            logger.error(f"Error generating embeddings with Gemini: {str(e)}")
            raise
    
    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_name
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for Gemini (768)."""
        return 768
