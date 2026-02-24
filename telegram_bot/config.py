"""
Telegram Bot Configuration.
Loads bot settings from environment.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

# Get project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"

class BotSettings(BaseSettings):
    """Bot configuration settings."""
    
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_admin_id: str = Field(default="", alias="TELEGRAM_ADMIN_ID")
    api_base_url: str = Field(default="http://localhost:8500", alias="API_BASE_URL")
    bot_api_email: str = Field(default="admin@tawasul.com", alias="BOT_API_EMAIL")
    bot_api_password: str = Field(default="admin123", alias="BOT_API_PASSWORD")
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
try:
    bot_settings = BotSettings()
except Exception:
    # Fallback to defaults if .env fails
    bot_settings = BotSettings(_env_file=None)
