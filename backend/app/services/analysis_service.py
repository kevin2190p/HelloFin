import os
import uuid
import time
import json
import structlog
from app.services.risk_scorer import calculate_risk_score
from app.services.llm_analyzer import analyze_with_qwen
from app.services.translation import translate_text
from app.services.huggingface_client import get_scam_probability
from app.models.schemas import WebhookResponse, TransactionRecord

logger = structlog.get_logger("hellofin.analysis")

async def process_message(
    redis,
    transcript: str,
    sender_phone: str,
    txn_id: str = None,
    is_new_payee: bool = False,
    transaction_amount: float = 0.0,
    message_type: str = "text",
) -> WebhookResponse:
    """
    Unified analysis engine for WhatsApp, Telegram, etc.
    Fuses keyword scoring and LLM analysis.
    """
    if not txn_id:
        txn_id = str(uuid.uuid4())
    
    timestamp = time.time()

    # Step 0: Translate if needed
    try:
        translated_text = await translate_text(transcript)
    except Exception as e:
        logger.error("translation_service_failed", error=str(e))
        translated_text = transcript
        
    if not translated_text:
        translated_text = transcript

    # Layer 1: Keyword Risk Scorer
    keyword_result = calculate_risk_score(
        transcript=transcript,
        caller_number=sender_phone,
        is_new_payee=is_new_payee,
        transaction_amount=transaction_amount,
    )
    keyword_score = keyword_result["risk_score"]

    # Layer 2: Qwen3 LLM Analysis
    try:
        llm_result = await analyze_with_qwen(
            text=translated_text,
            sender_phone=sender_phone,
        )
    except Exception as e:
        logger.error("llm_analysis_failed", error=str(e))
        llm_result = {"risk_score": 0, "confidence": 0, "risk_factors": []}
    
    llm_score = llm_result.get("risk_score", 0)
    llm_confidence = llm_result.get("confidence", 0)

    # Score Fusion
    if llm_confidence >= 70:
        llm_score = llm_result.get("risk_score", 0)
    llm_factors = llm_result.get("risk_factors", [])

    # Layer 3: HuggingFace specialized classification
    try:
        hf_prob = await get_scam_probability(translated_text)
    except Exception as e:
        logger.error("hf_classification_failed", error=str(e))
        hf_prob = 0.0
        
    hf_score = int(hf_prob * 100)
    
    # Fusion: 50% LLM, 30% Keyword, 20% HuggingFace
    hf_key_present = hf_score > 0
    llm_key_present = llm_score > 0
    
    if llm_key_present and hf_key_present:
        final_score = int((llm_score * 0.5) + (keyword_score * 0.3) + (hf_score * 0.2))
    elif llm_key_present:
        final_score = int((llm_score * 0.6) + (keyword_score * 0.4))
    else:
        # If AI fails, rely 100% on keywords
        final_score = keyword_score
    
    final_score = min(100, max(0, final_score))
    
    # Merge factors
    all_factors = keyword_result["risk_factors"] + llm_factors
    if hf_key_present:
        all_factors.append({
            "factor": "HuggingFace Confidence",
            "impact": hf_score,
            "detail": f"Specialized BERT model detected scam patterns with {hf_score}% confidence."
        })
    if llm_result.get("detected_tactics"):
        all_factors.append({
            "category": "llm_deep_analysis",
            "points": llm_score,
            "matches": llm_result.get("flagged_phrases", [])[:5],
            "description": f"Qwen3: {llm_result.get('explanation', '')}",
            "scam_type": llm_result.get("scam_type", "unknown"),
            "language": llm_result.get("language_detected", "unknown"),
        })

    threshold_high = 50 # Lowered for real-world testing/demonstration
    status = "held" if final_score >= threshold_high else "cleared"

    logger.warning("verdict",
                   txn_id=txn_id,
                   sender=sender_phone,
                   message_type=message_type,
                   final_score=final_score,
                   status=status)

    # Store in Redis
    record = TransactionRecord(
        txn_id=txn_id,
        sender_phone=sender_phone,
        transcript=transcript,
        translation=translated_text,
        risk_score=final_score,
        risk_factors=all_factors,
        is_new_payee=is_new_payee,
        transaction_amount=transaction_amount,
        status=status,
        timestamp=timestamp,
    )

    await redis.hset(f"txn:{txn_id}", mapping=record.model_dump_redis())
    
    # Push to caregiver alerts if risk is high
    if status == "held":
        await redis.sadd("txn:pending", txn_id)
        auto_cancel_sec = int(os.getenv("AUTO_CANCEL_SECONDS", "600"))
        await redis.setex(f"txn:timer:{txn_id}", auto_cancel_sec, "pending")
        
        # Create alert for the dashboard
        alert = {
            "txn_id": txn_id,
            "risk_score": final_score,
            "sender_phone": sender_phone,
            "transaction_amount": transaction_amount,
            "reason": f"{message_type.replace('_', ' ').title()}: {llm_result.get('scam_type', 'Suspicious message')}",
            "timestamp": timestamp,
            "status": "held",
            "transcript": transcript,
            "translation": translated_text if translated_text != transcript else None
        }
        await redis.lpush("caregiver:alerts", json.dumps(alert))
        logger.info("caregiver_alert_pushed", txn_id=txn_id)

    return WebhookResponse(
        txn_id=txn_id,
        transcript=transcript,
        translation=translated_text,
        risk_score=final_score,
        risk_factors=all_factors,
        status=status,
        auto_cancel_after_sec=600 if status == "held" else None,
    )
