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

from app.services.gemini_analyzer import get_gemini_explanation, analyze_risk_with_gemini

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
    Fuses keyword scoring and multiple LLM layers (Groq, Gemini, HuggingFace).
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

    # Layer 1: Groq LLM Analysis (Llama 3.3 70B)
    try:
        llm_result = await analyze_with_qwen(
            text=translated_text,
            sender_phone=sender_phone,
        )
    except Exception as e:
        logger.error("llm_analysis_failed", error=str(e))
        llm_result = {"risk_score": 0, "confidence": 0, "risk_factors": []}
    
    llm_score = llm_result.get("risk_score", 0)
    llm_factors = llm_result.get("risk_factors", [])

    # Layer 2: Gemini 1.5 Flash Analysis
    try:
        gemini_result = await analyze_risk_with_gemini(
            text=translated_text,
            sender_phone=sender_phone,
        )
    except Exception as e:
        logger.error("gemini_analysis_failed", error=str(e))
        gemini_result = {"risk_score": 0, "confidence": 0}
    
    gemini_score = gemini_result.get("risk_score", 0)

    # Layer 3: HuggingFace specialized classification
    try:
        hf_prob = await get_scam_probability(translated_text)
    except Exception as e:
        logger.error("hf_classification_failed", error=str(e))
        hf_prob = 0.0
        
    hf_score = int(hf_prob * 100)
    
    # --- AI FUSION ENGINE (3-Way Multi-LLM Consensus) ---
    # Weighting: 50% Groq (Llama), 30% Gemini, 20% HuggingFace (BERT)
    final_score = int((llm_score * 0.5) + (gemini_score * 0.3) + (hf_score * 0.2))
    
    if final_score == 0:
        # If AI returns nothing, fallback to Keywords
        keyword_result = calculate_risk_score(
            transcript=transcript,
            caller_number=sender_phone,
            is_new_payee=is_new_payee,
            transaction_amount=transaction_amount,
        )
        final_score = keyword_result["risk_score"]
        llm_factors = keyword_result["risk_factors"]
        logger.warning("ai_fusion_inactive", reason="AI models returned 0. Falling back to Keywords.")
    else:
        logger.info("ai_fusion_active", groq=llm_score, gemini=gemini_score, hf=hf_score, final=final_score)
    
    final_score = min(100, max(0, final_score))

    # --- GEMINI LOGICAL EXPLANATION ---
    try:
        gemini_reason = await get_gemini_explanation(translated_text, final_score)
        logger.info("gemini_explanation_generated", reason=gemini_reason)
    except Exception as e:
        logger.error("gemini_explanation_failed", error=str(e))
        gemini_reason = gemini_result.get("explanation") or "Analysis completed by AI Consensus engine."
    
    # Merge factors
    all_factors = llm_factors
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
            "description": f"Groq Llama 3.1: {llm_result.get('explanation', '')}",
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
        gemini_reason=gemini_reason
    )

    await redis.hset(f"txn:{txn_id}", mapping=record.model_dump_redis())
    
    # Always create an alert for the dashboard (Transparency)
    alert = {
        "txn_id": txn_id,
        "risk_score": final_score,
        "sender_phone": sender_phone,
        "transaction_amount": transaction_amount,
        "reason": gemini_reason, # Use Gemini reason for the dashboard alert
        "timestamp": timestamp,
        "status": status,  # "held" or "cleared"
        "transcript": transcript,
        "translation": translated_text if translated_text != transcript else None
    }
    await redis.lpush("caregiver:alerts", json.dumps(alert))
    await redis.ltrim("caregiver:alerts", 0, 99) # Keep last 100
    print(f"[DEBUG] 🚀 Alert Pushed to Redis: {txn_id} (Status: {status})")
    logger.info("dashboard_update_pushed", txn_id=txn_id, status=status)

    if status == "held":
        await redis.sadd("txn:pending", txn_id)
        auto_cancel_sec = int(os.getenv("AUTO_CANCEL_SECONDS", "600"))
        await redis.setex(f"txn:timer:{txn_id}", auto_cancel_sec, "pending")

    return WebhookResponse(
        txn_id=txn_id,
        transcript=transcript,
        translation=translated_text,
        risk_score=final_score,
        risk_factors=all_factors,
        status=status,
        auto_cancel_after_sec=600 if status == "held" else None,
        gemini_reason=gemini_reason
    )
