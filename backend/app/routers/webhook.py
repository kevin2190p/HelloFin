"""
Webhook Router – Receives messages from OpenClaw via n8n
=========================================================
POST /webhook/whatsapp-voice  → Voice note pipeline
POST /webhook/whatsapp-text   → Text message pipeline

Full pipeline:
  1. Receive from OpenClaw/n8n
  2. Voice: Groq Whisper STT → transcript
     Text: Use raw text directly
  3. Keyword risk scoring (fast, always runs)
  4. Qwen3 LLM analysis (deep, semantic)
  5. Fuse scores → final verdict
  6. Store in Redis
  7. Return verdict (triggers dashboard update)
"""

import os
import uuid
import time
from pathlib import Path

import structlog
from fastapi import APIRouter, File, Form, Request, UploadFile, HTTPException, Body
from pydantic import BaseModel

from app.services.whisper_client import transcribe_audio
from app.services.risk_scorer import calculate_risk_score
from app.services.llm_analyzer import analyze_with_qwen
from app.services.cloud_clients import upload_to_alibaba_oss
from app.models.schemas import WebhookResponse, TransactionRecord
from app.services.analysis_service import process_message

logger = structlog.get_logger("fakeout.webhook")

router = APIRouter()

AUDIO_DIR = Path("audios")
AUDIO_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────
# VOICE NOTE ENDPOINT
# ─────────────────────────────────────────────────────────────
@router.post("/whatsapp-voice", response_model=WebhookResponse)
async def receive_whatsapp_voice(
    request: Request,
    audio: UploadFile = File(...),
    sender_phone: str = Form(default="unknown"),
    is_new_payee: bool = Form(default=False),
    transaction_amount: float = Form(default=0.0),
):
    """
    Full voice note pipeline:
    OpenClaw → n8n → HERE → Groq Whisper → Qwen3 → Risk Score → Redis
    """
    txn_id = str(uuid.uuid4())
    redis = request.app.state.redis
    timestamp = time.time()

    # ── 1. Save audio ──────────────────────────────────────
    file_ext = Path(audio.filename or "voice.ogg").suffix or ".ogg"
    audio_path = AUDIO_DIR / f"{txn_id}{file_ext}"
    content = await audio.read()

    with open(audio_path, "wb") as f:
        f.write(content)

    logger.info("voice_received",
                txn_id=txn_id,
                sender=sender_phone,
                size_kb=round(len(content) / 1024, 1))

    # ── 1b. Upload to Alibaba OSS (best-effort) ────────────
    try:
        upload_to_alibaba_oss(
            file_path=str(audio_path),
            bucket=os.getenv("ALIBABA_OSS_BUCKET", "fakeout-audio-vault"),
            key=f"voice-notes/{txn_id}{file_ext}",
        )
    except Exception as e:
        logger.warning("oss_upload_skipped", error=str(e))

    # ── 2. Groq Whisper STT ───────────────────────────────
    try:
        transcript = await transcribe_audio(str(audio_path))
        logger.info("stt_transcript", txn_id=txn_id, preview=transcript[:100])
    except Exception as e:
        logger.error("stt_failed", txn_id=txn_id, error=str(e))
        raise HTTPException(status_code=502, detail=f"STT failed: {e}")

    return await process_message(
        redis=redis,
        txn_id=txn_id,
        transcript=transcript,
        sender_phone=sender_phone,
        is_new_payee=is_new_payee,
        transaction_amount=transaction_amount,
        message_type="voice",
    )


# ─────────────────────────────────────────────────────────────
# TEXT MESSAGE ENDPOINT
# ─────────────────────────────────────────────────────────────
class TextPayload(BaseModel):
    sender_phone: str = "unknown"
    text: str
    push_name: str = ""
    is_new_payee: bool = False
    transaction_amount: float = 0.0


@router.post("/whatsapp-text", response_model=WebhookResponse)
async def receive_whatsapp_text(
    request: Request,
    payload: TextPayload,
):
    """
    Text message pipeline:
    OpenClaw → n8n → HERE → Qwen3 LLM → Risk Score → Redis
    (No STT needed — text goes directly to Qwen3 + keyword engine)
    """
    txn_id = str(uuid.uuid4())
    redis = request.app.state.redis
    timestamp = time.time()

    logger.info("text_received",
                txn_id=txn_id,
                sender=payload.sender_phone,
                preview=payload.text[:80])

    return await process_message(
        redis=redis,
        txn_id=txn_id,
        transcript=payload.text,
        sender_phone=payload.sender_phone,
        is_new_payee=payload.is_new_payee,
        transaction_amount=payload.transaction_amount,
        message_type="text",
    )


