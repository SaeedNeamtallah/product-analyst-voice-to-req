"""
Application configuration routes.
Exposes provider availability and runtime selections.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List

from backend.config import settings
from backend.runtime_config import get_runtime_value, update_runtime_config
from backend.providers.llm.factory import LLMProviderFactory
from backend.providers.vectordb.factory import VectorDBProviderFactory

router = APIRouter(prefix="/config", tags=["App Config"])


class ProviderUpdate(BaseModel):
    llm_provider: str
    embedding_provider: str
    vector_db_provider: str | None = None
    retrieval_top_k: int | None = Field(default=None, ge=1)
    chunk_strategy: str | None = None
    chunk_size: int | None = Field(default=None, ge=100)
    chunk_overlap: int | None = Field(default=None, ge=0)
    parent_chunk_size: int | None = Field(default=None, ge=100)
    parent_chunk_overlap: int | None = Field(default=None, ge=0)
    retrieval_candidate_k: int | None = Field(default=None, ge=1)
    retrieval_hybrid_enabled: bool | None = None
    retrieval_hybrid_alpha: float | None = Field(default=None, ge=0.0, le=1.0)
    retrieval_rerank_enabled: bool | None = None
    retrieval_rerank_top_k: int | None = Field(default=None, ge=1)
    query_rewrite_enabled: bool | None = None
    voyage_output_dimension: int | None = Field(default=None, ge=128)


@router.get("/providers")
async def get_providers() -> Dict[str, object]:
    """Return available providers and current selections."""
    llm_available = LLMProviderFactory.get_available_providers()
    embedding_available = LLMProviderFactory.get_available_embedding_providers()
    vector_available = VectorDBProviderFactory.get_available_providers()

    return {
        "available": {
            "llm": llm_available,
            "embedding": embedding_available,
            "vector_db": vector_available,
        },
        "llm_provider": get_runtime_value("llm_provider", settings.llm_provider),
        "embedding_provider": get_runtime_value("embedding_provider", settings.embedding_provider),
        "vector_db_provider": get_runtime_value("vector_db_provider", settings.vector_db_provider),
        "retrieval_top_k": get_runtime_value("retrieval_top_k", settings.retrieval_top_k),
        "voyage_output_dimension": get_runtime_value("voyage_output_dimension", settings.voyage_output_dimension),
        "chunk_strategy": get_runtime_value("chunk_strategy", settings.chunk_strategy),
        "chunk_size": get_runtime_value("chunk_size", settings.chunk_size),
        "chunk_overlap": get_runtime_value("chunk_overlap", settings.chunk_overlap),
        "parent_chunk_size": get_runtime_value("parent_chunk_size", settings.parent_chunk_size),
        "parent_chunk_overlap": get_runtime_value("parent_chunk_overlap", settings.parent_chunk_overlap),
        "retrieval_candidate_k": get_runtime_value("retrieval_candidate_k", settings.retrieval_candidate_k),
        "retrieval_hybrid_enabled": get_runtime_value("retrieval_hybrid_enabled", settings.retrieval_hybrid_enabled),
        "retrieval_hybrid_alpha": get_runtime_value("retrieval_hybrid_alpha", settings.retrieval_hybrid_alpha),
        "retrieval_rerank_enabled": get_runtime_value("retrieval_rerank_enabled", settings.retrieval_rerank_enabled),
        "retrieval_rerank_top_k": get_runtime_value("retrieval_rerank_top_k", settings.retrieval_rerank_top_k),
        "query_rewrite_enabled": get_runtime_value("query_rewrite_enabled", settings.query_rewrite_enabled),
    }


@router.post("/providers")
async def update_providers(payload: ProviderUpdate) -> Dict[str, object]:
    """Update runtime provider selections."""
    llm_available = set(LLMProviderFactory.get_available_providers())
    embedding_available = set(LLMProviderFactory.get_available_embedding_providers())
    vector_available = set(VectorDBProviderFactory.get_available_providers())
    chunk_strategy_allowed = {"parent_child", "simple"}

    if payload.llm_provider not in llm_available:
        raise HTTPException(status_code=400, detail="Unsupported LLM provider")
    if payload.embedding_provider not in embedding_available:
        raise HTTPException(status_code=400, detail="Unsupported embedding provider")
    if payload.vector_db_provider is not None and payload.vector_db_provider not in vector_available:
        raise HTTPException(status_code=400, detail="Unsupported vector DB provider")
    if payload.chunk_strategy is not None and payload.chunk_strategy not in chunk_strategy_allowed:
        raise HTTPException(status_code=400, detail="Unsupported chunk strategy")

    updates = {
        "llm_provider": payload.llm_provider,
        "embedding_provider": payload.embedding_provider,
    }

    if payload.vector_db_provider is not None:
        updates["vector_db_provider"] = payload.vector_db_provider

    if payload.retrieval_top_k is not None:
        top_k = min(payload.retrieval_top_k, settings.retrieval_top_k_max)
        updates["retrieval_top_k"] = top_k

    if payload.chunk_strategy is not None:
        updates["chunk_strategy"] = payload.chunk_strategy
    if payload.chunk_size is not None:
        updates["chunk_size"] = payload.chunk_size
    if payload.chunk_overlap is not None:
        updates["chunk_overlap"] = payload.chunk_overlap
    if payload.parent_chunk_size is not None:
        updates["parent_chunk_size"] = payload.parent_chunk_size
    if payload.parent_chunk_overlap is not None:
        updates["parent_chunk_overlap"] = payload.parent_chunk_overlap
    if payload.retrieval_candidate_k is not None:
        updates["retrieval_candidate_k"] = payload.retrieval_candidate_k
    if payload.retrieval_hybrid_enabled is not None:
        updates["retrieval_hybrid_enabled"] = payload.retrieval_hybrid_enabled
    if payload.retrieval_hybrid_alpha is not None:
        updates["retrieval_hybrid_alpha"] = payload.retrieval_hybrid_alpha
    if payload.retrieval_rerank_enabled is not None:
        updates["retrieval_rerank_enabled"] = payload.retrieval_rerank_enabled
    if payload.retrieval_rerank_top_k is not None:
        updates["retrieval_rerank_top_k"] = payload.retrieval_rerank_top_k
    if payload.query_rewrite_enabled is not None:
        updates["query_rewrite_enabled"] = payload.query_rewrite_enabled
    if payload.voyage_output_dimension is not None:
        updates["voyage_output_dimension"] = payload.voyage_output_dimension

    config = update_runtime_config(updates)

    return {
        "llm_provider": config.get("llm_provider", settings.llm_provider),
        "embedding_provider": config.get("embedding_provider", settings.embedding_provider),
        "vector_db_provider": config.get("vector_db_provider", settings.vector_db_provider),
        "retrieval_top_k": config.get("retrieval_top_k", settings.retrieval_top_k),
        "voyage_output_dimension": config.get("voyage_output_dimension", settings.voyage_output_dimension),
        "chunk_strategy": config.get("chunk_strategy", settings.chunk_strategy),
        "chunk_size": config.get("chunk_size", settings.chunk_size),
        "chunk_overlap": config.get("chunk_overlap", settings.chunk_overlap),
        "parent_chunk_size": config.get("parent_chunk_size", settings.parent_chunk_size),
        "parent_chunk_overlap": config.get("parent_chunk_overlap", settings.parent_chunk_overlap),
        "retrieval_candidate_k": config.get("retrieval_candidate_k", settings.retrieval_candidate_k),
        "retrieval_hybrid_enabled": config.get("retrieval_hybrid_enabled", settings.retrieval_hybrid_enabled),
        "retrieval_hybrid_alpha": config.get("retrieval_hybrid_alpha", settings.retrieval_hybrid_alpha),
        "retrieval_rerank_enabled": config.get("retrieval_rerank_enabled", settings.retrieval_rerank_enabled),
        "retrieval_rerank_top_k": config.get("retrieval_rerank_top_k", settings.retrieval_rerank_top_k),
        "query_rewrite_enabled": config.get("query_rewrite_enabled", settings.query_rewrite_enabled),
    }

