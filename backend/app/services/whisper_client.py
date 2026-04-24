"""
Whisper Client – OpenAI Speech-to-Text Integration
===================================================
Transcribes voice notes using OpenAI's Whisper API.
Supports .ogg, .opus, .mp3, .wav, .m4a formats.
"""

import os
from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger("hellofin.whisper")

OPENAI_API_URL = "https://api.openai.com/v1/audio/transcriptions"


async def transcribe_audio(
    file_path: str,
    model: str = "whisper-1",
    language: str = "ms",  # Default to Malay; Whisper auto-detects if omitted
) -> str:
    """
    Transcribe an audio file using OpenAI Whisper API.

    Args:
        file_path: Path to the audio file on disk.
        model: Whisper model variant (default: whisper-1).
        language: ISO 639-1 language hint (ms=Malay, en=English, zh=Chinese).

    Returns:
        Transcribed text string.

    Raises:
        ValueError: If API key is missing.
        httpx.HTTPStatusError: If the API call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-REPLACE"):
        raise ValueError(
            "OPENAI_API_KEY not configured. "
            "Set it in .env to enable Whisper transcription."
        )

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    logger.info(
        "whisper_transcribe_start",
        file=str(file_path),
        size_kb=round(file_path.stat().st_size / 1024, 1),
        model=model,
    )

    # Build multipart form data
    with open(file_path, "rb") as audio_file:
        files = {
            "file": (file_path.name, audio_file, _mime_type(file_path.suffix)),
        }
        data = {
            "model": model,
            "response_format": "text",
        }
        # Only send language hint if explicitly set
        if language:
            data["language"] = language

        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                OPENAI_API_URL,
                headers=headers,
                files=files,
                data=data,
            )
            response.raise_for_status()

    transcript = response.text.strip()

    logger.info(
        "whisper_transcribe_done",
        file=str(file_path),
        transcript_length=len(transcript),
        preview=transcript[:100],
    )

    return transcript


def _mime_type(suffix: str) -> str:
    """Map file extension to MIME type for Whisper API."""
    mime_map = {
        ".ogg": "audio/ogg",
        ".opus": "audio/opus",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
    }
    return mime_map.get(suffix.lower(), "audio/ogg")
