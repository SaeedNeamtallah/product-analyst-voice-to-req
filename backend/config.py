"""
Configuration management using Pydantic Settings.
Loads environment variables from .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration (Docker on port 5435)
    database_url: str = Field(
        default="postgresql+asyncpg://ragmind:ragmind123@localhost:5435/ragmind",
        alias="DATABASE_URL"
    )
    
    # LLM Provider Configuration
    gemini_api_key: str = Field(
        default="",
        alias="GEMINI_API_KEY"
    )
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    gemini_lite_model: str = Field(default="gemini-2.5-lite-flash", alias="GEMINI_LITE_MODEL")
    embedding_provider: str = Field(default="gemini", alias="EMBEDDING_PROVIDER")
    gemini_embed_model: str = Field(
        default="models/gemini-embedding-001",
        alias="GEMINI_EMBED_MODEL"
    )
    cohere_api_key: str = Field(default="", alias="COHERE_API_KEY")
    cohere_embed_model: str = Field(
        default="embed-multilingual-v3.0",
        alias="COHERE_EMBED_MODEL"
    )
    cohere_max_batch_tokens: int = Field(
        default=50000,
        alias="COHERE_MAX_BATCH_TOKENS"
    )
    cohere_max_retries: int = Field(
        default=12,
        alias="COHERE_MAX_RETRIES"
    )
    cohere_base_retry_delay: float = Field(
        default=2.0,
        alias="COHERE_BASE_RETRY_DELAY"
    )
    voyage_api_key: str = Field(default="", alias="VOYAGE_API_KEY")
    voyage_embed_model: str = Field(default="voyage-3-large", alias="VOYAGE_EMBED_MODEL")
    voyage_output_dimension: int = Field(default=1024, alias="VOYAGE_OUTPUT_DIMENSION")
    hf_embedding_model: str = Field(default="BAAI/bge-m3", alias="HF_EMBED_MODEL")
    # OpenAI-compatible LLM providers
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL"
    )
    openrouter_gemini_2_flash_model: str = Field(
        default="google/gemini-2.0-flash-001",
        alias="OPENROUTER_GEMINI_2_FLASH_MODEL"
    )
    openrouter_free_model: str = Field(
        default="openrouter/free",
        alias="OPENROUTER_FREE_MODEL"
    )
    openrouter_site_url: str = Field(default="", alias="OPENROUTER_SITE_URL")
    openrouter_app_name: str = Field(default="", alias="OPENROUTER_APP_NAME")

    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        alias="GROQ_BASE_URL"
    )
    groq_llama_3_3_70b_versatile_model: str = Field(
        default="llama-3.3-70b-versatile",
        alias="GROQ_LLAMA_3_3_70B_VERSATILE_MODEL"
    )
    groq_gpt_oss_120b_model: str = Field(
        default="gpt-oss-120b",
        alias="GROQ_GPT_OSS_120B_MODEL"
    )

    cerebras_api_key: str = Field(default="", alias="CEREBRAS_API_KEY")
    cerebras_base_url: str = Field(
        default="https://api.cerebras.ai/v1",
        alias="CEREBRAS_BASE_URL"
    )
    cerebras_llama_3_3_70b_model: str = Field(
        default="llama-3.3-70b",
        alias="CEREBRAS_LLAMA_3_3_70B_MODEL"
    )
    cerebras_llama_3_1_8b_model: str = Field(
        default="llama-3.1-8b",
        alias="CEREBRAS_LLAMA_3_1_8B_MODEL"
    )
    cerebras_gpt_oss_120b_model: str = Field(
        default="gpt-oss-120b",
        alias="CEREBRAS_GPT_OSS_120B_MODEL"
    )
    embedding_batch_size: int = Field(default=20, alias="EMBEDDING_BATCH_SIZE")
    embedding_concurrency: int = Field(default=4, alias="EMBEDDING_CONCURRENCY")
    voyage_max_batch_tokens: int = Field(default=120000, alias="VOYAGE_MAX_BATCH_TOKENS")
    
    # Vector DB Configuration
    vector_db_provider: str = Field(default="pgvector", alias="VECTOR_DB_PROVIDER")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    qdrant_upsert_batch_size: int = Field(default=256, alias="QDRANT_UPSERT_BATCH_SIZE")
    
    # Storage Configuration
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_file_size_mb: int = Field(default=50, alias="MAX_FILE_SIZE_MB")
    
    # Chunking Configuration
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    parent_chunk_size: int = Field(default=3000, alias="PARENT_CHUNK_SIZE")
    parent_chunk_overlap: int = Field(default=600, alias="PARENT_CHUNK_OVERLAP")
    chunk_strategy: str = Field(default="parent_child", alias="CHUNK_STRATEGY")

    # Retrieval Configuration
    retrieval_top_k: int = Field(default=5, alias="RETRIEVAL_TOP_K")
    retrieval_top_k_max: int = Field(default=20, alias="RETRIEVAL_TOP_K_MAX")
    retrieval_candidate_k: int = Field(default=20, alias="RETRIEVAL_CANDIDATE_K")
    retrieval_hybrid_enabled: bool = Field(default=False, alias="RETRIEVAL_HYBRID_ENABLED")
    retrieval_hybrid_alpha: float = Field(default=0.7, alias="RETRIEVAL_HYBRID_ALPHA")
    retrieval_rerank_enabled: bool = Field(default=False, alias="RETRIEVAL_RERANK_ENABLED")
    retrieval_rerank_top_k: int = Field(default=10, alias="RETRIEVAL_RERANK_TOP_K")
    query_rewrite_enabled: bool = Field(default=False, alias="QUERY_REWRITE_ENABLED")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_title: str = Field(default="RAGMind API", alias="API_TITLE")
    api_version: str = Field(default="1.0.0", alias="API_VERSION")
    
    # Telegram Bot Configuration
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_admin_id: str = Field(default="", alias="TELEGRAM_ADMIN_ID")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        alias="CORS_ORIGINS"
    )
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance - use default values if .env not found
try:
    settings = Settings()
except Exception as e:
    # If .env is missing, use defaults
    import warnings
    warnings.warn(f".env file not found or invalid, using default settings: {str(e)}")
    # In Pydantic v2, we can't just pass _env_file=None to the constructor easily if it fails
    # We'll try to create a default instance without loading from env
    try:
        settings = Settings(_env_file=None)
    except:
        # Fallback to a very basic settings if even that fails
        settings = Settings()
