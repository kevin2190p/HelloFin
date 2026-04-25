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

logger = structlog.get_logger("hellofin.webhook")

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
            bucket=os.getenv("ALIBABA_OSS_BUCKET", "hellofin-audio-vault"),
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

    return await _process_and_respond(
        redis=redis,
        txn_id=txn_id,
        timestamp=timestamp,
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

    return await _process_and_respond(
        redis=redis,
        txn_id=txn_id,
        timestamp=timestamp,
        transcript=payload.text,
        sender_phone=payload.sender_phone,
        is_new_payee=payload.is_new_payee,
        transaction_amount=payload.transaction_amount,
        message_type="text",
    )


# ─────────────────────────────────────────────────────────────
# SHARED ANALYSIS ENGINE
# ─────────────────────────────────────────────────────────────
async def _process_and_respond(
    redis,
    txn_id: str,
    timestamp: float,
    transcript: str,
    sender_phone: str,
    is_new_payee: bool,
    transaction_amount: float,
    message_type: str,
) -> WebhookResponse:
    """
    Run dual-layer analysis: keyword engine + Qwen3 LLM.
    Fuse scores for final verdict.
    """

    # ── Layer 1: Keyword Risk Scorer (instant, <1ms) ───────
    keyword_result = calculate_risk_score(
        transcript=transcript,
        caller_number=sender_phone,
        is_new_payee=is_new_payee,
        transaction_amount=transaction_amount,
    )
    keyword_score = keyword_result["risk_score"]

    # ── Layer 2: Qwen3 LLM Analysis (deep, ~2-5s) ──────────
    llm_result = await analyze_with_qwen(
        text=transcript,
        sender_phone=sender_phone,
    )
    llm_score = llm_result.get("risk_score", 0)
    llm_confidence = llm_result.get("confidence", 0)

    # ── Score Fusion: weighted average ─────────────────────
    # LLM gets higher weight if confident (>70%), else equal split
    if llm_confidence >= 70:
        final_score = int(keyword_score * 0.35 + llm_score * 0.65)
    else:
        final_score = int(keyword_score * 0.6 + llm_score * 0.4)

    final_score = min(final_score, 100)

    # Merge risk factors from both layers
    all_factors = keyword_result.get("risk_factors", [])
    if llm_result.get("detected_tactics"):
        all_factors.append({
            "category": "llm_deep_analysis",
            "points": llm_score,
            "matches": llm_result.get("flagged_phrases", [])[:5],
            "description": f"Qwen3: {llm_result.get('explanation', '')}",
            "scam_type": llm_result.get("scam_type", "unknown"),
            "language": llm_result.get("language_detected", "unknown"),
        })

    threshold_high = int(os.getenv("RISK_THRESHOLD_HIGH", "80"))
    status = "held" if final_score >= threshold_high else "cleared"

    logger.warning("verdict",
                   txn_id=txn_id,
                   sender=sender_phone,
                   message_type=message_type,
                   keyword_score=keyword_score,
                   llm_score=llm_score,
                   final_score=final_score,
                   status=status,
                   is_scam=llm_result.get("is_scam"))

    # ── Store in Redis ──────────────────────────────────────
    record = TransactionRecord(
        txn_id=txn_id,
        sender_phone=sender_phone,
        transcript=transcript,
        risk_score=final_score,
        risk_factors=all_factors,
        is_new_payee=is_new_payee,
        transaction_amount=transaction_amount,
        status=status,
        timestamp=timestamp,
    )

    await redis.hset(f"txn:{txn_id}", mapping=record.model_dump_redis())
    if status == "held":
        await redis.sadd("txn:pending", txn_id)
        auto_cancel_sec = int(os.getenv("AUTO_CANCEL_SECONDS", "600"))
        await redis.setex(f"txn:timer:{txn_id}", auto_cancel_sec, "pending")

    return WebhookResponse(
        txn_id=txn_id,
        transcript=transcript,
        risk_score=final_score,
        risk_factors=all_factors,
        status=status,
        auto_cancel_after_sec=600 if status == "held" else None,
    )
