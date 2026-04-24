"""
Webhook Router – Receives WhatsApp voice notes from n8n / OpenClaw
==================================================================
POST /webhook/whatsapp-voice
  - Accepts audio file upload
  - Transcribes via Whisper
  - Scores risk
  - Stores result in Redis
  - Triggers hold if high risk
"""

import os
import uuid
import time
from pathlib import Path

import structlog
from fastapi import APIRouter, File, Form, Request, UploadFile, HTTPException

from app.services.whisper_client import transcribe_audio
from app.services.risk_scorer import calculate_risk_score
from app.services.cloud_clients import upload_to_alibaba_oss
from app.models.schemas import WebhookResponse, TransactionRecord

logger = structlog.get_logger("hellofin.webhook")

router = APIRouter()

AUDIO_DIR = Path("audios")
AUDIO_DIR.mkdir(exist_ok=True)


@router.post("/whatsapp-voice", response_model=WebhookResponse)
async def receive_whatsapp_voice(
    request: Request,
    audio: UploadFile = File(...),
    sender_phone: str = Form(default="unknown"),
    is_new_payee: bool = Form(default=False),
    transaction_amount: float = Form(default=0.0),
):
    """
    Receive a WhatsApp voice note, transcribe it, and score phishing risk.

    Flow:
    1. Save audio to disk (+ Alibaba OSS if configured)
    2. Transcribe with OpenAI Whisper
    3. Calculate risk score
    4. Store transaction in Redis
    5. Return risk assessment
    """
    txn_id = str(uuid.uuid4())
    redis = request.app.state.redis
    timestamp = time.time()

    # ── 1. Save audio locally ──────────────────────────────
    file_ext = Path(audio.filename or "voice.ogg").suffix or ".ogg"
    audio_path = AUDIO_DIR / f"{txn_id}{file_ext}"
    content = await audio.read()

    with open(audio_path, "wb") as f:
        f.write(content)

    logger.info("audio_received", txn_id=txn_id, sender=sender_phone,
                size_bytes=len(content), filename=audio.filename)

    # ── 1b. Upload to Alibaba OSS (async, non-blocking) ───
    try:
        upload_to_alibaba_oss(
            file_path=str(audio_path),
            bucket=os.getenv("ALIBABA_OSS_BUCKET", "hellofin-audio-vault"),
            key=f"voice-notes/{txn_id}{file_ext}",
        )
    except Exception as e:
        logger.warning("oss_upload_skipped", error=str(e))

    # ── 2. Transcribe with Whisper ─────────────────────────
    try:
        transcript = await transcribe_audio(str(audio_path))
    except Exception as e:
        logger.error("whisper_failed", txn_id=txn_id, error=str(e))
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e}")

    # ── 3. Calculate risk score ────────────────────────────
    risk_result = calculate_risk_score(
        transcript=transcript,
        caller_number=sender_phone,
        is_new_payee=is_new_payee,
        transaction_amount=transaction_amount,
    )

    # ── 4. Store in Redis ──────────────────────────────────
    record = TransactionRecord(
        txn_id=txn_id,
        sender_phone=sender_phone,
        transcript=transcript,
        risk_score=risk_result["risk_score"],
        risk_factors=risk_result["risk_factors"],
        is_new_payee=is_new_payee,
        transaction_amount=transaction_amount,
        status="held" if risk_result["risk_score"] >= 80 else "cleared",
        timestamp=timestamp,
    )

    await redis.hset(f"txn:{txn_id}", mapping=record.model_dump_redis())
    await redis.sadd("txn:pending", txn_id) if record.status == "held" else None

    # Set auto-cancel TTL (10 minutes) for held transactions
    if record.status == "held":
        auto_cancel_sec = int(os.getenv("AUTO_CANCEL_SECONDS", "600"))
        await redis.setex(f"txn:timer:{txn_id}", auto_cancel_sec, "pending")
        logger.warn("transaction_held", txn_id=txn_id,
                     risk_score=risk_result["risk_score"],
                     auto_cancel_sec=auto_cancel_sec)

    logger.info("risk_assessed", txn_id=txn_id,
                risk_score=risk_result["risk_score"],
                status=record.status)

    return WebhookResponse(
        txn_id=txn_id,
        transcript=transcript,
        risk_score=risk_result["risk_score"],
        risk_factors=risk_result["risk_factors"],
        status=record.status,
        auto_cancel_after_sec=600 if record.status == "held" else None,
    )
