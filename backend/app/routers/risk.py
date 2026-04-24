"""
Risk Scoring Router
===================
POST /risk/score – standalone risk scoring endpoint
Accepts transcript + context → returns detailed risk breakdown.
"""

import structlog
from fastapi import APIRouter

from app.models.schemas import RiskRequest, RiskResponse
from app.services.risk_scorer import calculate_risk_score
from app.services.cloud_clients import invoke_aws_lambda

logger = structlog.get_logger("hellofin.risk")

router = APIRouter()


@router.post("/score", response_model=RiskResponse)
async def score_risk(payload: RiskRequest):
    """
    Calculate risk score from transcript and context.

    Factors:
    - Keyword detection (urgency phrases, authority impersonation)
    - Unknown/international caller number
    - New payee flag
    - Transaction amount threshold
    - AWS Lambda fallback (optional)
    """
    result = calculate_risk_score(
        transcript=payload.transcript,
        caller_number=payload.caller_number,
        is_new_payee=payload.is_new_payee,
        transaction_amount=payload.transaction_amount,
    )

    # Optionally invoke AWS Lambda for secondary scoring
    lambda_score = None
    try:
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
    )
