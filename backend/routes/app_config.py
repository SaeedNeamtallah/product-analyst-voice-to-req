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
    embedding_provider: str
    retrieval_top_k: int | None = Field(default=None, ge=1)
    voyage_output_dimension: int | None = Field(default=None, ge=128)


@router.get("/providers")
async def get_providers(_user: User = Depends(get_current_user)) -> Dict[str, object]:
    """Return available providers and current selections."""
    llm_available = LLMProviderFactory.get_available_providers()
    embedding_available = LLMProviderFactory.get_available_embedding_providers()

    return {
        "available": {
            "llm": llm_available,
            "embedding": embedding_available,
        },
        "llm_provider": get_runtime_value("llm_provider", settings.llm_provider),
        "embedding_provider": get_runtime_value("embedding_provider", settings.embedding_provider),
        "retrieval_top_k": get_runtime_value("retrieval_top_k", settings.retrieval_top_k),
        "voyage_output_dimension": get_runtime_value("voyage_output_dimension", settings.voyage_output_dimension),
    }


@router.post("/providers")
async def update_providers(payload: ProviderUpdate, _user: User = Depends(get_current_user)) -> Dict[str, object]:
    """Update runtime provider selections."""
    llm_available = set(LLMProviderFactory.get_available_providers())
    embedding_available = set(LLMProviderFactory.get_available_embedding_providers())

    if payload.llm_provider not in llm_available:
        raise HTTPException(status_code=400, detail="Unsupported LLM provider")
    if payload.embedding_provider not in embedding_available:
        raise HTTPException(status_code=400, detail="Unsupported embedding provider")

    updates = {
        "llm_provider": payload.llm_provider,
        "embedding_provider": payload.embedding_provider,
    }

    if payload.retrieval_top_k is not None:
        top_k = min(payload.retrieval_top_k, settings.retrieval_top_k_max)
        updates["retrieval_top_k"] = top_k
    if payload.voyage_output_dimension is not None:
        updates["voyage_output_dimension"] = payload.voyage_output_dimension

    config = update_runtime_config(updates)

    return {
        "llm_provider": config.get("llm_provider", settings.llm_provider),
        "embedding_provider": config.get("embedding_provider", settings.embedding_provider),
        "retrieval_top_k": config.get("retrieval_top_k", settings.retrieval_top_k),
        "voyage_output_dimension": config.get("voyage_output_dimension", settings.voyage_output_dimension),
    }

