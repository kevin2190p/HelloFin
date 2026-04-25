"""
TNG eWallet & Caregiver Router
===============================
Pseudo TNG eWallet API for transaction hold, caregiver alerts,
and approve/cancel actions.
"""

import os
import time
import json

import structlog
from fastapi import APIRouter, Request, HTTPException

from app.models.schemas import (
    HoldResponse,
    HoldRequest,
    CaregiverAlert,
    ActionResponse,
)

logger = structlog.get_logger("fakeout.tng")

router = APIRouter()


async def _update_alert_status_in_list(redis, txn_id: str, new_status: str) -> bool:
    """Patch the matching alert entry inside the `caregiver:alerts` Redis list.

    The dashboard polls `caregiver:alerts` (a list of JSON strings) – approving
    or cancelling a transaction must mutate THIS list, otherwise the dashboard
    keeps showing the alert as "held" until it is trimmed off the end.

    Returns True when an entry was updated, False otherwise.
    """
    try:
        raw_alerts = await redis.lrange("caregiver:alerts", 0, 99)
    except Exception as e:
        logger.error("caregiver_alerts_lrange_failed", error=str(e))
        return False

    for idx, raw in enumerate(raw_alerts):
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if data.get("txn_id") != txn_id:
            continue
        data["status"] = new_status
        try:
            await redis.lset("caregiver:alerts", idx, json.dumps(data))
            logger.info(
                "caregiver_alert_status_synced",
                txn_id=txn_id,
                new_status=new_status,
                index=idx,
            )
            return True
        except Exception as e:
            logger.error(
                "caregiver_alert_lset_failed",
                txn_id=txn_id,
                error=str(e),
            )
            return False
    logger.warning(
        "caregiver_alert_not_found_in_list",
        txn_id=txn_id,
        new_status=new_status,
    )
    return False


@router.post("/tng/hold", response_model=HoldResponse)
async def hold_transaction(request: Request, payload: HoldRequest):
    """
    Simulate TNG eWallet transaction hold.

    If risk ≥ 80:
      - Returns {"status": "processing", "auto_cancel_after_sec": 600}
      - Money conceptually stays in Alibaba Cloud vault
      - AWS manages the deception layer (user sees "Processing")
    """
    redis = request.app.state.redis
    threshold = int(os.getenv("RISK_THRESHOLD_HIGH", "80"))

    if payload.risk_score < threshold:
        return HoldResponse(
            txn_id=payload.txn_id,
            status="cleared",
            message="Transaction risk below threshold, proceeding normally.",
            auto_cancel_after_sec=None,
        )

    auto_cancel_sec = int(os.getenv("AUTO_CANCEL_SECONDS", "600"))

    # Update Redis transaction status
    await redis.hset(f"txn:{payload.txn_id}", "status", "held")
    await redis.sadd("txn:pending", payload.txn_id)
    await redis.setex(f"txn:timer:{payload.txn_id}", auto_cancel_sec, "pending")

    # Create caregiver alert
    alert = {
        "txn_id": payload.txn_id,
        "risk_score": payload.risk_score,
        "sender_phone": payload.sender_phone,
        "transaction_amount": payload.transaction_amount,
        "reason": payload.reason or "High-risk voice phishing detected",
        "timestamp": time.time(),
        "status": "pending",
    }
    await redis.lpush("caregiver:alerts", json.dumps(alert))

    logger.warn(
        "transaction_held",
        txn_id=payload.txn_id,
        risk_score=payload.risk_score,
        auto_cancel_sec=auto_cancel_sec,
    )

    return HoldResponse(
        txn_id=payload.txn_id,
        status="processing",
        message="Transaction held for verification. Caregiver has been notified.",
        auto_cancel_after_sec=auto_cancel_sec,
    )


@router.get("/caregiver/alerts")
async def list_caregiver_alerts(request: Request):
    """
    List all transaction alerts. Newest first.
    """
    redis = request.app.state.redis
    # Get last 100 alerts from the list
    raw_alerts = await redis.lrange("caregiver:alerts", 0, 99)
    
    # DEBUG PRINT
    print(f"[DEBUG] 🔍 Dashboard Fetch: Found {len(raw_alerts)} total alerts in Redis/MockRedis")

    alerts = []
    for raw in raw_alerts:
        try:
            data = json.loads(raw)
            # Ensure essential fields for the dashboard
            if "status" not in data: data["status"] = "pending"
            if "timestamp" not in data: data["timestamp"] = time.time()
            if "risk_score" not in data: data["risk_score"] = 0
            
            alerts.append(data)
        except Exception:
            continue

    return alerts


@router.post("/caregiver/approve/{txn_id}", response_model=ActionResponse)
async def approve_transaction(request: Request, txn_id: str):
    """
    Caregiver approves a held transaction – funds are released.
    """
    redis = request.app.state.redis

    exists = await redis.exists(f"txn:{txn_id}")
    if not exists:
        raise HTTPException(status_code=404, detail="Transaction not found")

    current_status = await redis.hget(f"txn:{txn_id}", "status")
    if current_status != "held":
        raise HTTPException(
            status_code=400,
            detail=f"Transaction is '{current_status}', cannot approve",
        )

    await redis.hset(f"txn:{txn_id}", "status", "approved")
    await redis.srem("txn:pending", txn_id)
    await redis.delete(f"txn:timer:{txn_id}")
    await _update_alert_status_in_list(redis, txn_id, "approved")

    logger.info("transaction_approved", txn_id=txn_id)

    return ActionResponse(
        txn_id=txn_id,
        action="approved",
        message="Transaction approved by caregiver. Funds released.",
    )


@router.post("/caregiver/cancel/{txn_id}", response_model=ActionResponse)
async def cancel_transaction(request: Request, txn_id: str):
    """
    Caregiver cancels a held transaction – funds returned, scam blocked.
    """
    redis = request.app.state.redis

    exists = await redis.exists(f"txn:{txn_id}")
    if not exists:
        raise HTTPException(status_code=404, detail="Transaction not found")

    current_status = await redis.hget(f"txn:{txn_id}", "status")
    if current_status not in ("held", "pending"):
        raise HTTPException(
            status_code=400,
            detail=f"Transaction is '{current_status}', cannot cancel",
        )

    await redis.hset(f"txn:{txn_id}", "status", "cancelled")
    await redis.srem("txn:pending", txn_id)
    await redis.delete(f"txn:timer:{txn_id}")
    await _update_alert_status_in_list(redis, txn_id, "cancelled")

    logger.info("transaction_cancelled", txn_id=txn_id)

    return ActionResponse(
        txn_id=txn_id,
        action="cancelled",
        message="Transaction cancelled. Potential scam blocked successfully.",
    )
