"""
Chat Messages Router – WhatsApp Widget Feed
============================================
GET /chat/messages  → Returns recent intercepted messages for the widget
POST /chat/inject   → Simulate a message (for demo/testing without OpenClaw)
"""

import time
import json
from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class InjectPayload(BaseModel):
    sender_phone: str = "60163569782"
    push_name: str = "Unknown"
    message_type: str = "text"   # "text" or "voice"
    text: str = ""
    duration: int = 0


@router.get("/messages")
async def get_chat_messages(request: Request, limit: int = 20):
    """
    Returns the last N intercepted messages from Redis for the WhatsApp widget.
    Pulls from txn:* keys and formats them as chat bubbles.
    """
    redis = request.app.state.redis

    # Get all transaction IDs
    txn_ids = await redis.keys("txn:*")
    # Filter out timer keys
    txn_ids = [k for k in txn_ids if not k.startswith("txn:timer:") and not k.startswith("txn:pending")]

    messages = []
    for key in txn_ids[-limit:]:
        data = await redis.hgetall(key)
        if not data:
            continue
        messages.append({
            "id": data.get("txn_id", key.split(":")[-1]),
            "from": "scammer",
            "type": data.get("message_type", "text"),
            "text": data.get("transcript", ""),
            "duration": int(data.get("duration", 0)),
            "time": _format_time(float(data.get("timestamp", time.time()))),
            "risk_score": int(data.get("risk_score", 0)),
            "risk_level": data.get("status", "cleared").upper(),
            "llm_label": _extract_llm_label(data.get("risk_factors", "[]")),
            "scanning": False,
            "sender_phone": data.get("sender_phone", "unknown"),
        })

    # Sort by timestamp
    messages.sort(key=lambda m: m.get("time", ""))
    return messages


@router.post("/inject")
async def inject_message(request: Request, payload: InjectPayload):
    """
    Simulate a message without OpenClaw — for testing and demo.
    Immediately triggers the detection pipeline.
    """
    from app.routers.webhook import _process_and_respond
    import uuid

    txn_id = str(uuid.uuid4())
    redis = request.app.state.redis
    timestamp = time.time()

    result = await _process_and_respond(
        redis=redis,
        txn_id=txn_id,
        timestamp=timestamp,
        transcript=payload.text,
        sender_phone=payload.sender_phone,
        is_new_payee=False,
        transaction_amount=0.0,
        message_type=payload.message_type,
    )

    return {
        "status": "injected",
        "txn_id": txn_id,
        "risk_score": result.risk_score,
        "verdict": result.status,
    }


def _format_time(ts: float) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%I:%M %p")


def _extract_llm_label(factors_json: str) -> Optional[str]:
    try:
        factors = json.loads(factors_json)
        for f in factors:
            if f.get("category") == "llm_deep_analysis":
                return f.get("scam_type", "").replace("_", " ").title()
    except Exception:
        pass
    return None
