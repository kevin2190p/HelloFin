import os
import httpx
import structlog
from pathlib import Path

logger = structlog.get_logger("hellofin.whisper")

GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
HF_WHISPER_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"

async def transcribe_audio(file_path: str, language: str = None) -> str:
    """
    Transcribe audio with Groq and a HuggingFace fallback for maximum reliability.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    hf_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()

    # Attempt 1: Groq (Fastest)
    if groq_key and not groq_key.startswith("REPLACE"):
        try:
            logger.info("stt_attempt_groq", file=path.name)
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(path, "rb") as f:
                    # Rename to .m4a to trick the decoder
                    files = {"file": ("voice.m4a", f, "audio/mp4")}
                    data = {"model": "whisper-large-v3"}
                    if language: data["language"] = language
                    
                    resp = await client.post(
                        GROQ_AUDIO_URL,
                        headers={"Authorization": f"Bearer {groq_key}"},
                        files=files,
                        data=data
                    )
                    if resp.status_code == 200:
                        return resp.json().get("text", "").strip()
                    logger.warn("groq_stt_failed_falling_back", status=resp.status_code)
        except Exception as e:
            logger.warn("groq_stt_error", error=str(e))

    # Attempt 2: HuggingFace (More Flexible with formats)
    if hf_key and not hf_key.startswith("REPLACE"):
        try:
            logger.info("stt_attempt_huggingface", file=path.name)
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(path, "rb") as f:
                    resp = await client.post(
                        HF_WHISPER_URL,
                        headers={"Authorization": f"Bearer {hf_key}"},
                        content=f.read()
                    )
                    if resp.status_code == 200:
                        return resp.json().get("text", "").strip()
                    logger.error("hf_stt_failed", status=resp.status_code, body=resp.text)
        except Exception as e:
            logger.error("hf_stt_error", error=str(e))

    raise ValueError("All STT attempts failed. Please ensure your API keys are correct.")
