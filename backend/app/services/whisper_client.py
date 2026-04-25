"""
Whisper Client – Groq Speech-to-Text Integration
=================================================
Transcribes voice notes using Groq's whisper-large-v3 model.
Groq is 10x faster than OpenAI Whisper and supports Malay/English.
Supports .ogg, .opus, .mp3, .wav, .m4a, .webm formats.

Fallback: OpenAI Whisper if GROQ_API_KEY not set.
"""

import os
from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger("hellofin.whisper")

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
OPENAI_API_URL = "https://api.openai.com/v1/audio/transcriptions"


async def transcribe_audio(
    file_path: str,
    language: str = None,  # None = auto-detect (handles Malay + English mixed)
) -> str:
    """
    Transcribe an audio file using Groq Whisper large-v3.

    Groq's Whisper large-v3 handles:
      - Malaysian Malay (BM)
      - Manglish (mixed Malay/English)
      - Mandarin (basic)
      - English with Malaysian accent

    Args:
        file_path: Path to the audio file on disk.
        language: Optional ISO 639-1 language hint. None = auto-detect.

    Returns:
        Transcribed text string.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    file_size_kb = round(file_path.stat().st_size / 1024, 1)
    logger.info("stt_start", file=str(file_path), size_kb=file_size_kb)

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if groq_key and not groq_key.startswith("REPLACE"):
        transcript = await _transcribe_groq(file_path, groq_key, language)
    elif openai_key and not openai_key.startswith("sk-REPLACE"):
        logger.warning("stt_fallback_openai", reason="GROQ_API_KEY not set")
        transcript = await _transcribe_openai(file_path, openai_key, language)
    else:
        raise ValueError(
            "No STT API key configured. Set GROQ_API_KEY in .env"
        )

    logger.info(
        "stt_done",
        file=str(file_path),
        length=len(transcript),
        preview=transcript[:120],
    )
    return transcript


async def _transcribe_groq(file_path: Path, api_key: str, language: str) -> str:
    """Call Groq Whisper large-v3 API."""
    mime = _mime_type(file_path.suffix)

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, mime)}
        data = {
            "model": "whisper-large-v3",
            "response_format": "text",
            "temperature": "0",  # Deterministic output
        }
        if language:
            data["language"] = language

        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                GROQ_API_URL,
                headers=headers,
                files=files,
                data=data,
            )
            resp.raise_for_status()

    return resp.text.strip()


async def _transcribe_openai(file_path: Path, api_key: str, language: str) -> str:
    """Fallback: Call OpenAI Whisper-1 API."""
    mime = _mime_type(file_path.suffix)

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, mime)}
        data = {
            "model": "whisper-1",
            "response_format": "text",
        }
        if language:
            data["language"] = language

        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                OPENAI_API_URL,
                headers=headers,
                files=files,
                data=data,
            )
            resp.raise_for_status()

    return resp.text.strip()


def _mime_type(suffix: str) -> str:
    """Map file extension to MIME type."""
    return {
        ".ogg": "audio/ogg",
        ".opus": "audio/opus",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
        ".amr": "audio/amr",
    }.get(suffix.lower(), "audio/ogg")
