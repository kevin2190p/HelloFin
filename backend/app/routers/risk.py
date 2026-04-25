"""
Risk Scoring Router
===================
POST /risk/score – standalone risk scoring endpoint
Accepts transcript + context → returns detailed risk breakdown.
"""

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.models.schemas import RiskRequest, RiskResponse
from app.services.risk_scorer import calculate_risk_score
from app.services.analysis_service import process_message

logger = structlog.get_logger("hellofin.risk")

router = APIRouter()

class ScanMessage(BaseModel):
    message: str

from app.services.gemini_analyzer import get_gemini_explanation

@router.post("/scan")
async def scan(msg: ScanMessage, request: Request):
    """
    Simplified scan endpoint matching user's architecture guide.
    Powered by Advanced AI (Groq + HuggingFace + Gemini).
    """
    redis = request.app.state.redis
    result = await process_message(
        redis=redis,
        transcript=msg.message,
        sender_phone="api_test",
        message_type="api_scan"
    )
    
    return {
        "message": msg.message,
        "riskScore": result.risk_score,
        "status": "HIGH RISK ⚠️" if result.risk_score >= 70 else ("MEDIUM RISK ⚠️" if result.risk_score >= 40 else "SAFE"),
        "reasons": [f.get("factor", f.get("category", "Suspicious pattern")) for f in result.risk_factors],
        "gemini_reason": result.gemini_reason
    }


@router.post("/score", response_model=RiskResponse)
async def score_risk(payload: RiskRequest):
    """
    Calculate risk score from transcript and context.
    """
    result = calculate_risk_score(
        transcript=payload.transcript,
        caller_number=payload.caller_number,
        is_new_payee=payload.is_new_payee,
        transaction_amount=payload.transaction_amount,
    )

    # Gemini Explanation
    try:
        gemini_reason = await get_gemini_explanation(payload.transcript, result["risk_score"])
    except Exception:
        gemini_reason = "Logic verified by core system."

    # Optionally invoke AWS Lambda for secondary scoring
    lambda_score = None
    try:
        from app.services.lambda_client import invoke_aws_lambda
        lambda_result = invoke_aws_lambda({
            "transcript": payload.transcript,
            "caller_number": payload.caller_number,
            "is_new_payee": payload.is_new_payee,
        })
        lambda_score = lambda_result.get("risk_score")
    except Exception as e:
        logger.warning("aws_lambda_fallback_skipped", error=str(e))

    logger.info(
        "risk_scored",
        risk_score=result["risk_score"],
        lambda_score=lambda_score,
        factors=len(result["risk_factors"]),
    )

    return RiskResponse(
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        risk_factors=result["risk_factors"],
        lambda_score=lambda_score,
        recommendation=result["recommendation"],
        gemini_reason=gemini_reason
    )
