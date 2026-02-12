"""
Speech-to-Text service using Groq Whisper only.
"""
from __future__ import annotations

import mimetypes
import os
import tempfile
import time
from dataclasses import dataclass
from typing import Dict

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
                wait = backoff * (2 ** attempt)
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
        return {"text": body.get("text", ""), "language": detected}

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
        return {"text": combined, "language": detected_lang}

    @staticmethod
    def _mime_type(file_path: str) -> str:
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "audio/mpeg"
