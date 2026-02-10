"""
OpenAI-compatible LLM provider implementation.
Supports OpenRouter, Groq, Cerebras, and other OpenAI-style APIs.
"""
from typing import List, Optional, Dict, Any, AsyncIterator
import logging
import httpx
import json

from backend.providers.llm.interface import LLMInterface

logger = logging.getLogger(__name__)


class OpenAICompatProvider(LLMInterface):
    """OpenAI-compatible LLM provider (text generation only)."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        provider_label: str,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.provider_label = provider_label
        self.extra_headers = extra_headers or {}
        logger.info(
            "%s provider initialized with model: %s",
            self.provider_label,
            self.model_name
        )

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload: Dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            headers.update(self.extra_headers)

            endpoint = f"{self.base_url}/chat/completions"
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            choices = data.get("choices") or []
            if not choices:
                raise ValueError("No choices returned from provider")

            message = choices[0].get("message") or {}
            content = message.get("content")
            if not content:
                raise ValueError("Empty content returned from provider")

            return content
        except Exception as e:
            logger.error("Error generating text with %s: %s", self.provider_label, str(e))
            raise

    async def generate_text_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream text token-by-token via SSE from OpenAI-compat endpoint."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload: Dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            headers.update(self.extra_headers)

            endpoint = f"{self.base_url}/chat/completions"
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", endpoint, headers=headers, json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = (
                                chunk.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content")
                            )
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(
                "Error streaming text with %s: %s", self.provider_label, str(e)
            )
            raise

    async def generate_embeddings(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        raise NotImplementedError(
            "OpenAICompatProvider does not support embeddings in this project."
        )

    def get_model_name(self) -> str:
        return self.model_name

    def get_embedding_dimension(self) -> int:
        return 0
