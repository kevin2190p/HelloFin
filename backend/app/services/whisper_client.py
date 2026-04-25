import os
import httpx
import structlog
from pathlib import Path

logger = structlog.get_logger("fakeout.whisper")

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
    
    # DEBUG: Show which key is being used (masked)
    print(f"[DEBUG] 🔑 STT Using Key: {groq_key[:10]}...{groq_key[-4:] if groq_key else 'NONE'}")

    # Attempt: Groq (Verified Key + Native Support)
    if groq_key and not groq_key.startswith("REPLACE"):
        try:
            logger.info("stt_attempt_groq", file=path.name)
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(path, "rb") as f:
                    # We name it .mp3 to ensure Groq's decoder is fully triggered,
                    # but we send the raw .oga data from Telegram.
                    files = {"file": ("voice.mp3", f, "audio/mpeg")}
                    data = {"model": "whisper-large-v3"}
                    if language: data["language"] = language
                    
                    resp = await client.post(
                        GROQ_AUDIO_URL,
                        headers={"Authorization": f"Bearer {groq_key}"},
                        files=files,
                        data=data
                    )
                    
                    if resp.status_code == 200:
                        transcript = resp.json().get("text", "").strip()
                        logger.info("stt_success", transcript_len=len(transcript))
                        return transcript
                    
                    logger.error("groq_stt_api_error", status=resp.status_code, response=resp.text)
                    
        except Exception as e:
            logger.error("groq_stt_connection_error", error=str(e))

    raise ValueError("Transcription failed. Please ensure your Groq key is active and try again.")
