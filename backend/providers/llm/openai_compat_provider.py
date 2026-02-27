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

    _FALLBACK_PROMPT_LIMIT_CHARS = 20000
    _FALLBACK_MIN_MAX_TOKENS = 10000

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        return headers

    def _build_payload(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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
        if isinstance(response_format, dict) and response_format:
            payload["response_format"] = response_format
        return payload

    def _shrink_request(
        self,
        prompt: str,
        max_tokens: Optional[int],
    ) -> tuple[str, Optional[int]]:
        reduced_prompt = prompt
        if len(prompt) > self._FALLBACK_PROMPT_LIMIT_CHARS:
            reduced_prompt = prompt[: self._FALLBACK_PROMPT_LIMIT_CHARS]

        reduced_max_tokens = max_tokens
        if max_tokens is not None:
            reduced_max_tokens = max(
                self._FALLBACK_MIN_MAX_TOKENS,
                max_tokens // 2,
            )

        logger.warning(
            "%s returned 413. Retrying with smaller payload (prompt chars: %s -> %s, max_tokens: %s -> %s)",
            self.provider_label,
            len(prompt),
            len(reduced_prompt),
            max_tokens,
            reduced_max_tokens,
        )
        return reduced_prompt, reduced_max_tokens

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
        headers = self._build_headers()
        endpoint = f"{self.base_url}/chat/completions"

        current_prompt = prompt
        current_max_tokens = max_tokens
        response_format = kwargs.get("response_format") if isinstance(kwargs.get("response_format"), dict) else None

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                data: Optional[Dict[str, Any]] = None
                for attempt in range(2):
                    payload = self._build_payload(
                        prompt=current_prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=current_max_tokens,
                        response_format=response_format,
                    )

                    response = await client.post(endpoint, headers=headers, json=payload)

                    try:
                        response.raise_for_status()
                        data = response.json()
                        break
                    except httpx.HTTPStatusError:
                        should_retry = response.status_code == 413 and attempt == 0
                        if not should_retry:
                            raise

                        current_prompt, current_max_tokens = self._shrink_request(
                            prompt=current_prompt,
                            max_tokens=current_max_tokens,
                        )

                if data is None:
                    raise ValueError("No response returned from provider")

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
