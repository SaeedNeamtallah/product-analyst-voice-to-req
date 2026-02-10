"""
LLM Provider Factory.
Creates LLM provider instances based on configuration.
"""
from backend.providers.llm.interface import LLMInterface
from backend.providers.llm.gemini_provider import GeminiProvider
from backend.providers.llm.openai_compat_provider import OpenAICompatProvider
from backend.config import settings
from backend.runtime_config import get_runtime_value
import logging

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""
    
    @staticmethod
    def create_provider(provider_name: str = None) -> LLMInterface:
        """
        Create LLM provider instance.
        
        Args:
            provider_name: Name of provider ('gemini', 'openai', etc.)
                          Defaults to settings.llm_provider
        
        Returns:
            LLM provider instance
            
        Raises:
            ValueError: If provider name is not supported
        """
        provider_name = provider_name or get_runtime_value("llm_provider", settings.llm_provider)
        provider_name = provider_name.lower()

        if provider_name in {"gemini", "gemini-2.5-lite-flash"}:
            logger.info("Creating Gemini LLM provider")
            return GeminiProvider()

        if provider_name == "openrouter-gemini-2.0-flash":
            logger.info("Creating OpenRouter Gemini 2.0 Flash provider")
            extra_headers = {}
            if settings.openrouter_site_url:
                extra_headers["HTTP-Referer"] = settings.openrouter_site_url
            if settings.openrouter_app_name:
                extra_headers["X-Title"] = settings.openrouter_app_name
            return OpenAICompatProvider(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                model_name=settings.openrouter_gemini_2_flash_model,
                provider_label="OpenRouter",
                extra_headers=extra_headers
            )

        if provider_name == "openrouter-free":
            logger.info("Creating OpenRouter Free provider")
            extra_headers = {}
            if settings.openrouter_site_url:
                extra_headers["HTTP-Referer"] = settings.openrouter_site_url
            if settings.openrouter_app_name:
                extra_headers["X-Title"] = settings.openrouter_app_name
            return OpenAICompatProvider(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                model_name=settings.openrouter_free_model,
                provider_label="OpenRouter",
                extra_headers=extra_headers
            )

        if provider_name == "groq-llama-3.3-70b-versatile":
            logger.info("Creating Groq Llama 3.3 70B Versatile provider")
            return OpenAICompatProvider(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                model_name=settings.groq_llama_3_3_70b_versatile_model,
                provider_label="Groq"
            )

        if provider_name == "groq-gpt-oss-120b":
            logger.info("Creating Groq GPT-oss 120B provider")
            return OpenAICompatProvider(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                model_name=settings.groq_gpt_oss_120b_model,
                provider_label="Groq"
            )

        if provider_name == "cerebras-llama-3.3-70b":
            logger.info("Creating Cerebras Llama 3.3 70B provider")
            return OpenAICompatProvider(
                api_key=settings.cerebras_api_key,
                base_url=settings.cerebras_base_url,
                model_name=settings.cerebras_llama_3_3_70b_model,
                provider_label="Cerebras"
            )

        if provider_name == "cerebras-llama-3.1-8b":
            logger.info("Creating Cerebras Llama 3.1 8B provider")
            return OpenAICompatProvider(
                api_key=settings.cerebras_api_key,
                base_url=settings.cerebras_base_url,
                model_name=settings.cerebras_llama_3_1_8b_model,
                provider_label="Cerebras"
            )

        if provider_name == "cerebras-gpt-oss-120b":
            logger.info("Creating Cerebras GPT-oss 120B provider")
            return OpenAICompatProvider(
                api_key=settings.cerebras_api_key,
                base_url=settings.cerebras_base_url,
                model_name=settings.cerebras_gpt_oss_120b_model,
                provider_label="Cerebras"
            )
        
        # Add more providers here as needed
        # elif provider_name == "openai":
        #     return OpenAIProvider()
        # elif provider_name == "cohere":
        #     return CohereProvider()
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")

    @staticmethod
    def create_embedding_provider(provider_name: str = None) -> LLMInterface:
        """
        Create embedding provider instance.

        Args:
            provider_name: Name of provider ('gemini', 'cohere', etc.)
                          Defaults to settings.embedding_provider

        Returns:
            LLM provider instance
        """
        provider_name = provider_name or get_runtime_value("embedding_provider", settings.embedding_provider)
        provider_name = provider_name.lower()

        if provider_name == "gemini":
            logger.info("Creating Gemini embedding provider")
            return GeminiProvider()

        if provider_name == "cohere":
            from backend.providers.llm.cohere_provider import CohereProvider
            logger.info("Creating Cohere embedding provider")
            return CohereProvider()

        if provider_name == "voyage":
            from backend.providers.llm.voyage_provider import VoyageProvider
            logger.info("Creating Voyage embedding provider")
            return VoyageProvider()

        if provider_name in {"bge-m3", "hf-bge-m3"}:
            from backend.providers.llm.hf_bge_m3_provider import BgeM3Provider
            logger.info("Creating BGE-M3 embedding provider")
            return BgeM3Provider()

        raise ValueError(f"Unsupported embedding provider: {provider_name}")
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available provider names."""
        return [
            "gemini",
            "gemini-2.5-lite-flash",
            "openrouter-gemini-2.0-flash",
            "openrouter-free",
            "groq-llama-3.3-70b-versatile",
            "groq-gpt-oss-120b",
            "cerebras-llama-3.3-70b",
            "cerebras-llama-3.1-8b",
            "cerebras-gpt-oss-120b",
        ]

    @staticmethod
    def get_available_embedding_providers() -> list:
        """Get list of available embedding provider names."""
        return ["gemini", "cohere", "voyage", "bge-m3"]
