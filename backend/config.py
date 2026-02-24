"""
Configuration management using Pydantic Settings.
Loads environment variables from .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List
import json
import secrets
import warnings
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration (Docker on port 5555)
    database_url: str = Field(
        default="postgresql+asyncpg://tawasul:tawasul123@localhost:5555/tawasul",
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
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        alias="OPENAI_BASE_URL"
    )
    openai_stt_model: str = Field(default="whisper-1", alias="OPENAI_STT_MODEL")
    groq_llama_3_3_70b_versatile_model: str = Field(
        default="llama-3.3-70b-versatile",
        alias="GROQ_LLAMA_3_3_70B_VERSATILE_MODEL"
    )

    cerebras_api_key: str = Field(default="", alias="CEREBRAS_API_KEY")
    cerebras_base_url: str = Field(
        default="https://api.cerebras.ai/v1",
        alias="CEREBRAS_BASE_URL"
    )
    cerebras_llama_3_3_70b_model: str = Field(
        default="llama3.3-70b",
        alias="CEREBRAS_LLAMA_3_3_70B_MODEL"
    )
    cerebras_llama_3_1_8b_model: str = Field(
        default="llama3.1-8b",
        alias="CEREBRAS_LLAMA_3_1_8B_MODEL"
    )
    
    # Storage Configuration
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_file_size_mb: int = Field(default=50, alias="MAX_FILE_SIZE_MB")
    stt_max_file_size_mb: int = Field(default=500, alias="STT_MAX_FILE_SIZE_MB")
    object_storage_provider: str = Field(default="local", alias="OBJECT_STORAGE_PROVIDER")
    aws_s3_bucket: str = Field(default="", alias="AWS_S3_BUCKET")
    aws_s3_region: str = Field(default="us-east-1", alias="AWS_S3_REGION")
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_s3_endpoint_url: str = Field(default="", alias="AWS_S3_ENDPOINT_URL")
    aws_s3_presign_expiry_seconds: int = Field(default=900, alias="AWS_S3_PRESIGN_EXPIRY_SECONDS")
    
    # Chunking Configuration
    chunk_size: int = Field(default=30000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    parent_chunk_size: int = Field(default=300000, alias="PARENT_CHUNK_SIZE")
    parent_chunk_overlap: int = Field(default=600, alias="PARENT_CHUNK_OVERLAP")
    chunk_strategy: str = Field(default="parent_child", alias="CHUNK_STRATEGY")

    # API Configuration
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8500, alias="API_PORT")
    api_title: str = Field(default="Tawasul API", alias="API_TITLE")
    api_version: str = Field(default="1.0.0", alias="API_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    strict_startup_checks: bool = Field(default=False, alias="STRICT_STARTUP_CHECKS")

    # Redis (shared state for stateless API workers)
    redis_enabled: bool = Field(default=True, alias="REDIS_ENABLED")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_key_prefix: str = Field(default="tawasul", alias="REDIS_KEY_PREFIX")
    redis_max_connections: int = Field(default=200, alias="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: float = Field(default=2.0, alias="REDIS_SOCKET_TIMEOUT")
    redis_connect_timeout: float = Field(default=2.0, alias="REDIS_CONNECT_TIMEOUT")
    redis_health_check_interval: int = Field(default=30, alias="REDIS_HEALTH_CHECK_INTERVAL")
    redis_state_ttl_seconds: int = Field(default=86400, alias="REDIS_STATE_TTL_SECONDS")
    redis_draft_ttl_seconds: int = Field(default=604800, alias="REDIS_DRAFT_TTL_SECONDS")
    redis_require_tls: bool = Field(default=False, alias="REDIS_REQUIRE_TLS")
    redis_ssl_cert_reqs: str = Field(default="required", alias="REDIS_SSL_CERT_REQS")
    redis_username: str = Field(default="", alias="REDIS_USERNAME")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    
    # Telegram Bot Configuration
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_admin_id: str = Field(default="", alias="TELEGRAM_ADMIN_ID")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8500",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8500",
        ],
        alias="CORS_ORIGINS"
    )

    @field_validator("cors_origins", mode="after")
    @classmethod
    def _normalize_cors_origins(cls, value: List[str]) -> List[str]:
        required = [
            "http://localhost:3000",
            "http://localhost:8500",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8500",
        ]
        normalized = list(value or [])
        for origin in required:
            if origin not in normalized:
                normalized.append(origin)
        return normalized
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Authentication
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiry_hours: int = Field(default=72, alias="JWT_EXPIRY_HOURS")

    @field_validator("jwt_secret", mode="after")
    @classmethod
    def _ensure_jwt_secret(cls, v: str) -> str:
        _INSECURE_DEFAULT = "tawasul-secret-change-me-in-production"
        if not v or v == _INSECURE_DEFAULT:
            warnings.warn(
                "JWT_SECRET not set or using insecure default. "
                "A random secret has been generated for this session. "
                "Set JWT_SECRET in .env for persistent tokens across restarts.",
                stacklevel=2,
            )
            return secrets.token_urlsafe(64)
        return v

    @field_validator("environment", mode="after")
    @classmethod
    def _normalize_environment(cls, value: str) -> str:
        env = str(value or "development").strip().lower()
        if env not in {"development", "staging", "production"}:
            return "development"
        return env
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def _validate_production_basics(self, errors_list: List[str], jwt_secret_from_env: str) -> None:
        if not jwt_secret_from_env:
            errors_list.append("JWT_SECRET must be explicitly set in production.")
        if "*" in self.cors_origins:
            errors_list.append("CORS_ORIGINS must not include '*' in production.")

    def _validate_production_redis(self, errors_list: List[str]) -> None:
        if not self.redis_enabled:
            errors_list.append("REDIS_ENABLED must be true in production for shared worker state.")
        if not str(self.redis_url or "").strip():
            errors_list.append("REDIS_URL must be set in production.")
        if self.redis_require_tls and not str(self.redis_url or "").strip().startswith("rediss://"):
            errors_list.append("REDIS_REQUIRE_TLS=true requires REDIS_URL to start with rediss://")

        redis_password = str(self.redis_password or "").strip()
        redis_url = str(self.redis_url or "").strip()
        if not redis_password and "@" not in redis_url:
            errors_list.append("Redis authentication must be configured in production (REDIS_PASSWORD or credentialed REDIS_URL).")

        cert_reqs = str(self.redis_ssl_cert_reqs or "required").strip().lower()
        if cert_reqs not in {"required", "optional", "none"}:
            errors_list.append("REDIS_SSL_CERT_REQS must be one of: required|optional|none")

    def _validate_provider_configuration(
        self,
        env: str,
        warnings_list: List[str],
        errors_list: List[str],
    ) -> None:
        selected_provider = str(self.llm_provider or "").strip().lower()

        def emit(message: str) -> None:
            (errors_list if env == "production" else warnings_list).append(message)

        if selected_provider == "gemini" and not str(self.gemini_api_key or "").strip():
            emit("LLM_PROVIDER=gemini but GEMINI_API_KEY is empty.")
        if selected_provider.startswith("openrouter") and not str(self.openrouter_api_key or "").strip():
            emit("OpenRouter provider selected but OPENROUTER_API_KEY is empty.")
        if selected_provider.startswith("groq") and not str(self.groq_api_key or "").strip():
            emit("Groq provider selected but GROQ_API_KEY is empty.")

    def startup_issues(self) -> tuple[List[str], List[str]]:
        """Return (warnings, errors) for startup hardening checks."""
        warnings_list: List[str] = []
        errors_list: List[str] = []

        env = self.environment
        jwt_secret_from_env = str(os.getenv("JWT_SECRET", "")).strip()
        if env == "production":
            self._validate_production_basics(errors_list, jwt_secret_from_env)
            self._validate_production_redis(errors_list)

        self._validate_provider_configuration(env, warnings_list, errors_list)

        return warnings_list, errors_list

    def validate_startup_or_raise(self) -> None:
        warnings_list, errors_list = self.startup_issues()
        for msg in warnings_list:
            warnings.warn(msg, stacklevel=2)

        must_fail = bool(errors_list) and (self.environment == "production" or self.strict_startup_checks)
        if must_fail:
            joined = " | ".join(errors_list)
            raise RuntimeError(f"Startup validation failed: {joined}")


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
    except Exception:
        # Fallback to a very basic settings if even that fails
        settings = Settings()
