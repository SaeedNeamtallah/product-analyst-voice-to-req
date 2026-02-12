"""
Speech-to-Text routes (Groq Whisper only).
"""
from __future__ import annotations

import os
import uuid
from typing import Dict

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import settings
from backend.services.stt_service import (
    GroqWhisperProvider,
    SUPPORTED_LANGUAGES,
    is_allowed_file,
)

router = APIRouter(prefix="/stt", tags=["Speech-to-Text"])


class TranscribeResponse(BaseModel):
    success: bool
    text: str
    language: str
    provider: str


@router.get("/providers")
async def list_providers() -> Dict[str, object]:
    configured = bool(settings.groq_api_key)
    return {
        "providers": [
            {
                "name": "groq",
                "display_name": "Groq Whisper",
                "configured": configured,
            }
        ],
        "default": "groq",
    }


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("auto"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    if not is_allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Invalid file format")

    if language != "auto" and language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")

    file_bytes = await file.read()
    file_size = len(file_bytes)
    max_size = settings.stt_max_file_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.stt_max_file_size_mb} MB.",
        )

    ext = os.path.splitext(file.filename)[1].lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(settings.upload_dir, "stt")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_name)

    try:
        async with aiofiles.open(file_path, "wb") as handle:
            await handle.write(file_bytes)

        provider = GroqWhisperProvider(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )
        result = provider.transcribe_auto(file_path, language)

        detected_lang = result.get("language", language)
        lang_label = SUPPORTED_LANGUAGES.get(detected_lang, detected_lang)

        return {
            "success": True,
            "text": result.get("text", ""),
            "language": lang_label,
            "provider": "groq",
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
