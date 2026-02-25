"""
Bot Configuration Routes.
API endpoints for configuring the Telegram bot.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import httpx
from telegram_bot.config import bot_settings
from backend.database.models import User
from backend.routes.auth import get_current_user
from backend.runtime_config import get_runtime_value, update_runtime_config

router = APIRouter(prefix="/bot", tags=["Bot Config"])

# Path to .env file
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

# Keys we manage for Telegram config
_TG_ENV_KEYS = {
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ADMIN_ID",
    "BOT_API_EMAIL",
    "BOT_API_PASSWORD",
    "API_BASE_URL",
}


class BotConfig(BaseModel):
    active_project_id: Optional[int] = None


class TelegramConfigUpdate(BaseModel):
    telegram_bot_token: Optional[str] = None
    telegram_admin_id: Optional[str] = None
    bot_api_email: Optional[str] = None
    bot_api_password: Optional[str] = None
    api_base_url: Optional[str] = None


def _read_env_values() -> dict[str, str]:
    """Read relevant Telegram keys from .env file."""
    values: dict[str, str] = {}
    if not _ENV_PATH.exists():
        return values
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, val = stripped.partition("=")
        key = key.strip()
        if key in _TG_ENV_KEYS:
            values[key] = val.strip()
    return values


def _write_env_values(updates: dict[str, str]) -> None:
    """Update specific keys in .env file, preserving all other content."""
    if not _ENV_PATH.exists():
        lines_out = []
    else:
        lines_out = _ENV_PATH.read_text(encoding="utf-8").splitlines()

    keys_written: set[str] = set()

    for i, line in enumerate(lines_out):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.partition("=")[0].strip()
        if key in updates:
            lines_out[i] = f"{key}={updates[key]}"
            keys_written.add(key)

    # Append any keys that weren't already in the file
    for key, val in updates.items():
        if key not in keys_written:
            lines_out.append(f"{key}={val}")

    _ENV_PATH.write_text("\n".join(lines_out) + "\n", encoding="utf-8")


def _mask_token(token: str) -> str:
    """Mask bot token, showing only first 8 and last 4 chars."""
    if not token or len(token) < 16:
        return "***"
    return token[:8] + ":" + "*" * 30 + token[-4:]


@router.get("/telegram-config")
async def get_telegram_config(_user: User = Depends(get_current_user)):
    """Return current Telegram bot configuration (token is masked)."""
    env = _read_env_values()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    return {
        "telegram_bot_token": _mask_token(token) if token else "",
        "telegram_admin_id": env.get("TELEGRAM_ADMIN_ID", ""),
        "bot_api_email": env.get("BOT_API_EMAIL", "admin@tawasul.com"),
        "bot_api_password": "",  # Never return password
        "api_base_url": env.get("API_BASE_URL", "http://localhost:8500"),
        "has_token": bool(token),
    }


@router.post("/telegram-config")
async def update_telegram_config(
    payload: TelegramConfigUpdate,
    _user: User = Depends(get_current_user),
):
    """Save Telegram bot configuration to .env file."""
    updates: dict[str, str] = {}

    if payload.telegram_bot_token is not None and payload.telegram_bot_token.strip():
        updates["TELEGRAM_BOT_TOKEN"] = payload.telegram_bot_token.strip()
    if payload.telegram_admin_id is not None:
        updates["TELEGRAM_ADMIN_ID"] = payload.telegram_admin_id.strip()
    if payload.bot_api_email is not None and payload.bot_api_email.strip():
        updates["BOT_API_EMAIL"] = payload.bot_api_email.strip()
    if payload.bot_api_password is not None and payload.bot_api_password.strip():
        updates["BOT_API_PASSWORD"] = payload.bot_api_password.strip()
    if payload.api_base_url is not None and payload.api_base_url.strip():
        updates["API_BASE_URL"] = payload.api_base_url.strip()

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    try:
        _write_env_values(updates)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")

    return {"status": "success", "updated_keys": list(updates.keys())}


@router.get("/config")
async def get_bot_config(_user: User = Depends(get_current_user)):
    """Get current bot configuration."""
    return {
        "active_project_id": get_runtime_value("bot_active_project_id", None),
    }

@router.post("/config")
async def update_bot_config(config: BotConfig, _user: User = Depends(get_current_user)):
    """Update bot configuration (active project)."""
    current_config = {
        "active_project_id": get_runtime_value("bot_active_project_id", None),
    }
    if config.active_project_id is not None:
        current_config["active_project_id"] = config.active_project_id
        update_runtime_config({"bot_active_project_id": config.active_project_id})
    return current_config

@router.post("/profile")
async def update_bot_profile(
    name: str = Form(...),
    _user: User = Depends(get_current_user),
):
    """
    Update Telegram Bot Profile (Name).
    Requires 'setMyName' permission.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Update Name
            url = f"https://api.telegram.org/bot{bot_settings.telegram_bot_token}/setMyName"
            response = await client.post(url, json={"name": name})
            response.raise_for_status()
            
            return {"status": "success", "message": "Bot profile updated"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

