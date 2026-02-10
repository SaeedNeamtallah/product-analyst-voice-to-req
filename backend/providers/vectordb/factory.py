"""
VectorDB Provider Factory.
Creates vector database provider instances based on configuration.
"""
from backend.providers.vectordb.interface import VectorDBInterface
from backend.providers.vectordb.pgvector_provider import PGVectorProvider
from backend.providers.vectordb.qdrant_provider import QdrantProvider
from backend.config import settings
from backend.runtime_config import get_runtime_value
import logging

logger = logging.getLogger(__name__)


class VectorDBProviderFactory:
    """Factory for creating VectorDB provider instances."""
    
    _instances = {}
    
    @classmethod
    def create_provider(cls, provider_name: str = None) -> VectorDBInterface:
        """
        Create or return existing VectorDB provider instance (Singleton).
        
        Args:
            provider_name: Name of provider ('pgvector', 'qdrant', etc.)
                          Defaults to settings.vector_db_provider
        
        Returns:
            VectorDB provider instance
            
        Raises:
            ValueError: If provider name is not supported
        """
        provider_name = provider_name or get_runtime_value("vector_db_provider", settings.vector_db_provider)
        provider_name = provider_name.lower()
        
        if provider_name in cls._instances:
            return cls._instances[provider_name]
        
        if provider_name == "pgvector":
            logger.info("Creating PGVector provider")
            instance = PGVectorProvider()
        
        elif provider_name == "qdrant":
            logger.info("Creating Qdrant provider")
            instance = QdrantProvider(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key
            )
        
        else:
            raise ValueError(f"Unsupported VectorDB provider: {provider_name}")
            
        cls._instances[provider_name] = instance
        return instance
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available provider names."""
        return ["pgvector", "qdrant"]
