"""
Abstract LLM Provider Interface.
Defines the contract that all LLM providers must implement.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator


class LLMInterface(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion from prompt.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass

    async def generate_text_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream text completion token by token.

        Default implementation falls back to non-streaming generate_text
        and yields the whole response at once.
        """
        full = await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        yield full
    
    @abstractmethod
    async def generate_embeddings(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """
        Generate vector embeddings for texts.
        
        Args:
            texts: List of text strings to embed
            **kwargs: Additional provider-specific parameters
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the model name/identifier.
        
        Returns:
            Model name string
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Get the embedding vector dimension.
        
        Returns:
            Dimension size as integer
        """
        pass
