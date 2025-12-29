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
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:Ezz123456@localhost:5432/ragmind",
        alias="DATABASE_URL"
    )
    
    # LLM Provider Configuration
    gemini_api_key: str = Field(
        default="AIzaSyD2N-rsmfER9P2dZznBh4wXKAFZRajJ0eU",
        alias="GEMINI_API_KEY"
    )
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    gemini_model: str = Field(default="gemma-3-12b-it", alias="GEMINI_MODEL")
    
    # Vector DB Configuration
    vector_db_provider: str = Field(default="pgvector", alias="VECTOR_DB_PROVIDER")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    
    # Storage Configuration
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_file_size_mb: int = Field(default=50, alias="MAX_FILE_SIZE_MB")
    
    # Chunking Configuration
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    
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
