"""
Bot Configuration Routes.
API endpoints for configuring the Telegram bot.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import Optional
import httpx
from telegram_bot.config import bot_settings
from backend.database.models import User
from backend.routes.auth import get_current_user
from backend.runtime_config import get_runtime_value, update_runtime_config

router = APIRouter(prefix="/bot", tags=["Bot Config"])

class BotConfig(BaseModel):
    active_project_id: Optional[int] = None


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@router.get("/config")
async def get_bot_config(_user: User = Depends(_require_admin)):
    """Get current bot configuration."""
    return {
        "active_project_id": get_runtime_value("bot_active_project_id", None),
    }

@router.post("/config")
async def update_bot_config(config: BotConfig, _user: User = Depends(_require_admin)):
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
