"""
Bot Configuration Routes.
API endpoints for configuring the Telegram bot.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import Optional
import json
import os
import httpx
from telegram_bot.config import bot_settings
from backend.database.models import User
from backend.routes.auth import get_current_user

router = APIRouter(prefix="/bot", tags=["Bot Config"])

CONFIG_FILE = "bot_config.json"

class BotConfig(BaseModel):
    active_project_id: Optional[int] = None


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

@router.get("/config")
async def get_bot_config(_user: User = Depends(_require_admin)):
    """Get current bot configuration."""
    return load_config()

@router.post("/config")
async def update_bot_config(config: BotConfig, _user: User = Depends(_require_admin)):
    """Update bot configuration (active project)."""
    current_config = load_config()
    if config.active_project_id is not None:
        current_config["active_project_id"] = config.active_project_id
    save_config(current_config)
    return current_config

@router.post("/profile")
async def update_bot_profile(
    name: str = Form(...),
    _user: User = Depends(_require_admin),
    # image: UploadFile = File(None) # Image upload to be implemented if needed
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
