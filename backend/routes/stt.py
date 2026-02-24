"""
Speech-to-Text routes with provider failover and circuit-breaker protection.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Dict

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import settings
from backend.providers.llm.factory import LLMProviderFactory
from backend.services.stt_service import (
    GroqWhisperProvider,
    OpenAIWhisperProvider,
    SUPPORTED_LANGUAGES,
    is_allowed_file,
)
from backend.services.resilience_service import run_with_failover, circuit_breakers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stt", tags=["Speech-to-Text"])
UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024


class TranscribeResponse(BaseModel):
    success: bool
    text: str
    language: str
    provider: str
    confidence: float | None = None
    requires_confirmation: bool = True
    quality_warnings: list[str] = []


def _validate_transcribe_request(file: UploadFile, language: str) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    if not is_allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Invalid file format")

    if language != "auto" and language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")


def _build_provider_calls(file_path: str, language: str):
    provider_calls = []

    if settings.groq_api_key:
        groq_provider = GroqWhisperProvider(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )
        provider_calls.append(("groq", lambda: _transcribe_async(groq_provider, file_path, language)))

    if settings.openai_api_key:
        openai_provider = OpenAIWhisperProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model_name=settings.openai_stt_model,
        )
        provider_calls.append(("openai", lambda: _transcribe_async(openai_provider, file_path, language)))

    return provider_calls


async def post_process_stt_text(text: str) -> str:
    """Uses LLM to fix messy STT outputs, especially for Egyptian Arabic."""
    if not text or not text.strip():
        return text
    
    system_prompt = """أنت خبير في معالجة وتصحيح النصوص.
النص المُدخل هو مخرجات من نموذج تحويل الصوت إلى نص (Speech-to-Text) لعميل يتحدث باللهجة المصرية. 
قد يحتوي النص على أخطاء استماع، كلمات غير مفهومة، تداخل في الحروف، أو مصطلحات إنجليزية نُطقت بعامية (عك).

مهمتك:
1. تصحيح الأخطاء الإملائية والكلمات المشوهة لتوضيح المعنى الحقيقي.
2. الحفاظ على روح الكلام ومقصده، يمكنك إبقاء اللهجة المصرية الواضحة أو استخدام فصحى مبسطة.
3. يُمنع منعاً باتاً تغيير المعنى الأصلي، أو إضافة أي معلومات/متطلبات من عندك.
4. أعد النص المصحح فقط وبدون أي مقدمات، أو شروحات، أو علامات تنصيص."""

    try:
        # استخدام الـ LLM Provider المتاح حالياً في النظام
        llm = LLMProviderFactory.create_provider()
        corrected_text = await llm.generate_text(
            prompt=text,
            system_prompt=system_prompt,
            temperature=0.1,  # حرارة منخفضة جداً لمنع الهلوسة والتركيز على التصحيح فقط
            max_tokens=1500
        )
        return corrected_text.strip()
    except Exception as e:
        logger.error(f"Error in STT post-processing: {e}")
        # في حالة فشل الـ LLM لأي سبب، نرجع النص الأصلي حتى لا يتعطل النظام
        return text


def _format_transcribe_response(result: Dict[str, object], used_provider: str, language: str) -> Dict[str, object]:
    detected_lang = result.get("language", language)
    lang_label = SUPPORTED_LANGUAGES.get(detected_lang, detected_lang)
    quality = result.get("quality") if isinstance(result.get("quality"), dict) else {}

    return {
        "success": True,
        "text": result.get("text", ""),
        "language": lang_label,
        "provider": used_provider,
        "confidence": quality.get("confidence"),
        "requires_confirmation": bool(quality.get("requires_confirmation", True)),
        "quality_warnings": quality.get("warnings") if isinstance(quality.get("warnings"), list) else [],
    }


@router.get("/providers")
async def list_providers() -> Dict[str, object]:
    groq_configured = bool(settings.groq_api_key)
    openai_configured = bool(settings.openai_api_key)
    groq_circuit_open = await circuit_breakers.is_open("stt:groq")
    openai_circuit_open = await circuit_breakers.is_open("stt:openai")
    providers = [
        {
            "name": "groq",
            "display_name": "Groq Whisper",
            "configured": groq_configured,
            "circuit_open": groq_circuit_open,
        },
        {
            "name": "openai",
            "display_name": "OpenAI Whisper",
            "configured": openai_configured,
            "circuit_open": openai_circuit_open,
        },
    ]
    return {
        "providers": providers,
        "default": "groq",
    }


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("auto"),
):
    _validate_transcribe_request(file=file, language=language)

    max_size = settings.stt_max_file_size_mb * 1024 * 1024

    ext = os.path.splitext(file.filename)[1].lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(settings.upload_dir, "stt")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_name)

    try:
        await _stream_upload_to_disk(
            file=file,
            destination_path=file_path,
            max_size_bytes=max_size,
            chunk_size_bytes=UPLOAD_CHUNK_SIZE_BYTES,
        )

        provider_calls = _build_provider_calls(file_path=file_path, language=language)

        if not provider_calls:
            raise HTTPException(status_code=503, detail="No STT providers configured")

        result, used_provider = await run_with_failover(
            provider_calls,
            breaker_prefix="stt",
            failure_threshold=2,
            cooldown_seconds=60,
        )

        # ====== بداية التعديل: تنظيف النص باستخدام LLM ======
        original_text = result.get("text", "")
        if original_text:
            corrected_text = await post_process_stt_text(original_text)
            result["text"] = corrected_text
            
            # يمكنك إرسال رسالة للـ Console للتأكد من الفرق
            logger.info(f"Original STT: {original_text}")
            logger.info(f"Corrected STT: {corrected_text}")
        # ====================================================

        return _format_transcribe_response(result=result, used_provider=used_provider, language=language)
    except RuntimeError as exc:
        detail = str(exc)
        if "No available providers" in detail or "All providers failed" in detail:
            raise HTTPException(
                status_code=503,
                detail="Speech transcription is temporarily unavailable. Please type your message manually.",
            ) from exc
        raise HTTPException(status_code=500, detail=detail) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await file.close()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass


async def _transcribe_async(provider, file_path: str, language: str) -> Dict[str, object]:
    return await asyncio.to_thread(provider.transcribe_auto, file_path, language)


async def _stream_upload_to_disk(
    file: UploadFile,
    destination_path: str,
    max_size_bytes: int,
    chunk_size_bytes: int,
) -> int:
    total_bytes = 0
    async with aiofiles.open(destination_path, "wb") as handle:
        while True:
            chunk = await file.read(chunk_size_bytes)
            if not chunk:
                break

            total_bytes += len(chunk)
            if total_bytes > max_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {settings.stt_max_file_size_mb} MB.",
                )

            await handle.write(chunk)

    return total_bytes
