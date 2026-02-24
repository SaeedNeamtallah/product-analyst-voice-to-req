"""
Speech-to-Text service providers (Groq Whisper + OpenAI Whisper fallback).
"""
from __future__ import annotations

import mimetypes
import os
import tempfile
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import httpx


ALLOWED_EXTENSIONS = {"wav", "mp3", "mp4", "mpeg", "mpga", "m4a", "webm", "ogg"}
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "auto": "Auto-detect",
    "ar": "Arabic",
    "en": "English",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "tr": "Turkish",
    "nl": "Dutch",
    "pl": "Polish",
    "sv": "Swedish",
    "hi": "Hindi",
    "ur": "Urdu",
    "fa": "Persian",
}


def is_allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _retry_request(fn, max_retries: int = 3, backoff: float = 2.0) -> httpx.Response:
    last_exc = None
    for attempt in range(max_retries):
        try:
            return fn()
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            code = exc.response.status_code
            if code == 429 or code >= 500:
                retry_after = exc.response.headers.get("Retry-After") if exc.response is not None else None
                if retry_after and str(retry_after).strip().isdigit():
                    wait = float(str(retry_after).strip())
                else:
                    wait = backoff * (2 ** attempt)
                wait = min(wait, 8.0) + random.uniform(0, 0.25)
                time.sleep(wait)
                continue
            raise
    raise last_exc


@dataclass
class GroqWhisperProvider:
    api_key: str
    base_url: str = "https://api.groq.com/openai/v1"

    name: str = "groq"
    display_name: str = "Groq Whisper"
    max_file_bytes: int = 24 * 1024 * 1024
    chunk_duration_s: int = 10 * 60

    @staticmethod
    def _compute_quality(body: Dict[str, Any], text: str) -> Dict[str, Any]:
        segments = body.get("segments") if isinstance(body.get("segments"), list) else []
        avg_logprob_values: List[float] = []
        no_speech_values: List[float] = []

        for segment in segments:
            if not isinstance(segment, dict):
                continue
            avg_lp = segment.get("avg_logprob")
            no_speech = segment.get("no_speech_prob")
            if isinstance(avg_lp, (int, float)):
                avg_logprob_values.append(float(avg_lp))
            if isinstance(no_speech, (int, float)):
                no_speech_values.append(float(no_speech))

        avg_logprob = (sum(avg_logprob_values) / len(avg_logprob_values)) if avg_logprob_values else None
        avg_no_speech = (sum(no_speech_values) / len(no_speech_values)) if no_speech_values else None

        words = [w for w in str(text or "").strip().split() if w.strip()]
        word_count = len(words)
        suspicious_tokens = {"???", "[inaudible]", "inaudible", "...", "غير_مفهوم", "غير", "مفهوم"}
        suspicious_count = sum(1 for w in words if w.lower() in suspicious_tokens)

        logprob_component = 0.6
        if avg_logprob is not None:
            logprob_component = max(0.0, min(1.0, (avg_logprob + 1.6) / 1.6))

        no_speech_component = 0.8
        if avg_no_speech is not None:
            no_speech_component = 1.0 - max(0.0, min(1.0, avg_no_speech))

        confidence = round((0.7 * logprob_component) + (0.3 * no_speech_component), 3)
        if suspicious_count > 0:
            confidence = round(max(0.0, confidence - min(0.3, suspicious_count * 0.08)), 3)
        if word_count < 4:
            confidence = round(max(0.0, confidence - 0.15), 3)

        warnings: List[str] = []
        if word_count < 4:
            warnings.append("Transcript is very short and may be incomplete.")
        if suspicious_count > 0:
            warnings.append("Transcript contains uncertain tokens that may indicate recognition errors.")
        if avg_no_speech is not None and avg_no_speech > 0.45:
            warnings.append("High non-speech probability detected; audio may be noisy or unclear.")
        if avg_logprob is not None and avg_logprob < -1.1:
            warnings.append("Low speech confidence from model segments.")

        requires_confirmation = confidence < 0.72 or bool(warnings)
        return {
            "confidence": confidence,
            "requires_confirmation": requires_confirmation,
            "warnings": warnings[:3],
            "stats": {
                "word_count": word_count,
                "avg_logprob": avg_logprob,
                "avg_no_speech_prob": avg_no_speech,
            },
        }

    @property
    def api_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/audio/transcriptions"

    def transcribe(self, file_path: str, language: str = "auto") -> dict:
        if not self.api_key:
            raise RuntimeError("Groq is not configured. Set GROQ_API_KEY in .env")

        filename = os.path.basename(file_path)
        mime = self._mime_type(file_path)

        data = {
            "model": "whisper-large-v3",
            "response_format": "verbose_json",
        }
        if language != "auto":
            data["language"] = language

        headers = {"Authorization": f"Bearer {self.api_key}"}

        with open(file_path, "rb") as file_handle:
            def do_request() -> httpx.Response:
                file_handle.seek(0)
                resp = httpx.post(
                    self.api_url,
                    headers=headers,
                    data=data,
                    files={"file": (filename, file_handle, mime)},
                    timeout=120,
                )
                resp.raise_for_status()
                return resp

            resp = _retry_request(do_request)

        body = resp.json()
        detected = body.get("language", language)
        text = body.get("text", "")
        quality = self._compute_quality(body=body, text=text)
        return {"text": text, "language": detected, "quality": quality}

    def transcribe_auto(self, file_path: str, language: str = "auto") -> dict:
        file_size = os.path.getsize(file_path)
        if file_size <= self.max_file_bytes:
            return self.transcribe(file_path, language)

        return self._chunked_transcribe(file_path, language)

    def _chunked_transcribe(self, file_path: str, language: str) -> dict:
        try:
            from pydub import AudioSegment
        except ImportError as exc:
            raise RuntimeError(
                "File is too large for Groq Whisper. Install pydub to enable chunking: "
                "uv pip install pydub (ffmpeg must be in PATH)."
            ) from exc

        audio = AudioSegment.from_file(file_path)
        chunk_ms = self.chunk_duration_s * 1000
        total_chunks = max(1, (len(audio) + chunk_ms - 1) // chunk_ms)

        all_text: list[str] = []
        detected_lang = language
        quality_scores: List[float] = []
        quality_warnings: List[str] = []
        temp_files: list[str] = []

        try:
            for i, start in enumerate(range(0, len(audio), chunk_ms)):
                chunk = audio[start : start + chunk_ms]

                tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                tmp.close()
                chunk.export(tmp.name, format="mp3", bitrate="128k")
                temp_files.append(tmp.name)

                result = self.transcribe(tmp.name, language)
                all_text.append(result.get("text", ""))
                quality = result.get("quality") if isinstance(result.get("quality"), dict) else {}
                score = quality.get("confidence")
                if isinstance(score, (int, float)):
                    quality_scores.append(float(score))
                warnings = quality.get("warnings") if isinstance(quality.get("warnings"), list) else []
                for warning in warnings:
                    if warning not in quality_warnings:
                        quality_warnings.append(str(warning))

                if i == 0 and result.get("language") and result["language"] != language:
                    detected_lang = result["language"]
                    if language == "auto":
                        language = detected_lang
        finally:
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

        combined = " ".join(t for t in all_text if t)
        confidence = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0.65
        quality = {
            "confidence": confidence,
            "requires_confirmation": confidence < 0.72 or bool(quality_warnings),
            "warnings": quality_warnings[:3],
            "stats": {
                "chunks": total_chunks,
                "word_count": len([w for w in combined.split() if w.strip()]),
            },
        }
        return {"text": combined, "language": detected_lang, "quality": quality}

    @staticmethod
    def _mime_type(file_path: str) -> str:
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "audio/mpeg"


@dataclass
class OpenAIWhisperProvider:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model_name: str = "whisper-1"

    name: str = "openai"
    display_name: str = "OpenAI Whisper"
    max_file_bytes: int = 24 * 1024 * 1024

    @property
    def api_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/audio/transcriptions"

    def transcribe_auto(self, file_path: str, language: str = "auto") -> dict:
        return self.transcribe(file_path=file_path, language=language)

    def transcribe(self, file_path: str, language: str = "auto") -> dict:
        if not self.api_key:
            raise RuntimeError("OpenAI STT is not configured. Set OPENAI_API_KEY in .env")

        filename = os.path.basename(file_path)
        mime = GroqWhisperProvider._mime_type(file_path)
        data = {
            "model": self.model_name,
            "response_format": "verbose_json",
        }
        if language != "auto":
            data["language"] = language

        headers = {"Authorization": f"Bearer {self.api_key}"}

        with open(file_path, "rb") as file_handle:
            def do_request() -> httpx.Response:
                file_handle.seek(0)
                resp = httpx.post(
                    self.api_url,
                    headers=headers,
                    data=data,
                    files={"file": (filename, file_handle, mime)},
                    timeout=120,
                )
                resp.raise_for_status()
                return resp

            resp = _retry_request(do_request)

        body = resp.json()
        detected = body.get("language", language)
        text = body.get("text", "")
        quality = GroqWhisperProvider._compute_quality(body=body, text=text)
        return {"text": text, "language": detected, "quality": quality}
