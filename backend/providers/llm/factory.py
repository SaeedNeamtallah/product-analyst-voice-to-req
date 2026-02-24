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

GEMINI_PROVIDER = "gemini"
GEMINI_FLASH_PROVIDER = "gemini-2.5-flash"
GEMINI_LITE_PROVIDER = "gemini-2.5-lite-flash"


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    _provider_cache: dict[str, LLMInterface] = {}

    @staticmethod
    def _openrouter_headers() -> dict:
        headers = {}
        if settings.openrouter_site_url:
            headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            headers["X-Title"] = settings.openrouter_app_name
        return headers
    
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

        cached = LLMProviderFactory._provider_cache.get(provider_name)
        if cached is not None:
            return cached

        if provider_name in {GEMINI_PROVIDER, GEMINI_FLASH_PROVIDER}:
            logger.info("Creating Gemini LLM provider: %s", settings.gemini_model)
            provider = GeminiProvider(model_name=settings.gemini_model)
            LLMProviderFactory._provider_cache[provider_name] = provider
            return provider

        if provider_name == GEMINI_LITE_PROVIDER:
            lite_model = getattr(settings, "gemini_lite_model", GEMINI_LITE_PROVIDER)
            logger.info("Creating Gemini LLM provider: %s", lite_model)
            provider = GeminiProvider(model_name=lite_model)
            LLMProviderFactory._provider_cache[provider_name] = provider
            return provider

        openrouter_models = {
            "openrouter-gemini-2.0-flash": settings.openrouter_gemini_2_flash_model,
            "openrouter-free": settings.openrouter_free_model,
        }
        openrouter_model = openrouter_models.get(provider_name)
        if openrouter_model:
            logger.info("Creating OpenRouter provider: %s", provider_name)
            provider = OpenAICompatProvider(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                model_name=openrouter_model,
                provider_label="OpenRouter",
                extra_headers=LLMProviderFactory._openrouter_headers()
            )
            LLMProviderFactory._provider_cache[provider_name] = provider
            return provider

        compat_providers = {
            "groq-llama-3.3-70b-versatile": {
                "api_key": settings.groq_api_key,
                "base_url": settings.groq_base_url,
                "model_name": settings.groq_llama_3_3_70b_versatile_model,
                "label": "Groq",
            },
            "cerebras-llama-3.3-70b": {
                "api_key": settings.cerebras_api_key,
                "base_url": settings.cerebras_base_url,
                "model_name": settings.cerebras_llama_3_3_70b_model,
                "label": "Cerebras",
            },
            "cerebras-llama-3.1-8b": {
                "api_key": settings.cerebras_api_key,
                "base_url": settings.cerebras_base_url,
                "model_name": settings.cerebras_llama_3_1_8b_model,
                "label": "Cerebras",
            },
        }
        compat_config = compat_providers.get(provider_name)
        if compat_config:
            logger.info("Creating %s provider", compat_config["label"])
            provider = OpenAICompatProvider(
                api_key=compat_config["api_key"],
                base_url=compat_config["base_url"],
                model_name=compat_config["model_name"],
                provider_label=compat_config["label"]
            )
            LLMProviderFactory._provider_cache[provider_name] = provider
            return provider

        raise ValueError(f"Unsupported LLM provider: {provider_name}")

    @staticmethod
    def get_available_providers() -> list:
        """Get list of available provider names (only those with API keys configured)."""
        providers = [GEMINI_PROVIDER]  # Gemini is always available if GEMINI_API_KEY is set

        if not settings.gemini_api_key:
            providers = []

        # Gemini lite variant shares the same key
        if settings.gemini_api_key:
            providers.append(GEMINI_FLASH_PROVIDER)
            providers.append(GEMINI_LITE_PROVIDER)

        if settings.openrouter_api_key:
            providers.append("openrouter-gemini-2.0-flash")
            providers.append("openrouter-free")

        if settings.groq_api_key:
            providers.append("groq-llama-3.3-70b-versatile")

        if settings.cerebras_api_key:
            providers.append("cerebras-llama-3.3-70b")
            providers.append("cerebras-llama-3.1-8b")

        return providers

    @staticmethod
    def get_available_embedding_providers() -> list:
        """Embedding providers are disabled in no-RAG mode."""
        return []

    @staticmethod
    def clear_cache() -> None:
        LLMProviderFactory._provider_cache.clear()
