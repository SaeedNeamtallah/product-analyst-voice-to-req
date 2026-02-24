"""
Application configuration routes.
Exposes provider availability and runtime selections.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List

from backend.config import settings
from backend.runtime_config import get_runtime_value, update_runtime_config
from backend.providers.llm.factory import LLMProviderFactory
from backend.database.models import User
from backend.routes.auth import get_current_user

router = APIRouter(prefix="/config", tags=["App Config"])


class ProviderUpdate(BaseModel):
    llm_provider: str


@router.get("/providers")
async def get_providers(_user: User = Depends(get_current_user)) -> Dict[str, object]:
    """Return available providers and current selections."""
    llm_available = LLMProviderFactory.get_available_providers()

    return {
        "available": {
            "llm": llm_available,
        },
        "llm_provider": get_runtime_value("llm_provider", settings.llm_provider),
    }


@router.post("/providers")
async def update_providers(payload: ProviderUpdate, _user: User = Depends(get_current_user)) -> Dict[str, object]:
    """Update runtime provider selections."""
    llm_available = set(LLMProviderFactory.get_available_providers())

    if payload.llm_provider not in llm_available:
        raise HTTPException(status_code=400, detail="Unsupported LLM provider")

    updates = {
        "llm_provider": payload.llm_provider,
    }

    config = update_runtime_config(updates)

    return {
        "llm_provider": config.get("llm_provider", settings.llm_provider),
    }

