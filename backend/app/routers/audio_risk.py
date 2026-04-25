import structlog
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.whisper_client import transcribe_audio
from app.services.translation import translate_text
from app.services.llm_analyzer import analyze_with_qwen

logger = structlog.get_logger("fakeout.audio_risk")

router = APIRouter()

@router.post("/audio-risk")
async def audio_risk(file: UploadFile = File(...), language: str = None):
    """Accept an audio file, transcribe, translate to English, and run LLM scam analysis.
    Returns a JSON payload with transcription, translation, and risk analysis.
    """
    # Save to temporary location
    try:
        contents = await file.read()
        tmp_path = f"./tmp_{file.filename}"
        with open(tmp_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.error("audio_save_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to read uploaded file")

    try:
        transcription = await transcribe_audio(tmp_path, language)
    finally:
        # Clean up temporary file
        import os
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    if not transcription:
        raise HTTPException(status_code=500, detail="Transcription failed")

    translation = await translate_text(transcription)
    if not translation:
        # fallback to original transcription if translation not possible
        translation = transcription

    analysis = await analyze_with_qwen(translation)

    return {
        "transcription": transcription,
        "translation": translation,
        "analysis": analysis,
    }
