"""
Pydantic Schemas – Request/Response Models
"""
import json
from typing import Optional
from pydantic import BaseModel, Field


class RiskRequest(BaseModel):
    transcript: str
    caller_number: str = "unknown"
    is_new_payee: bool = False
    transaction_amount: float = 0.0


class RiskResponse(BaseModel):
    risk_score: int
    risk_level: str
    risk_factors: list[dict]
    lambda_score: Optional[int] = None
    recommendation: str


class WebhookResponse(BaseModel):
    txn_id: str
    transcript: str
    translation: Optional[str] = None
    risk_score: int
    risk_factors: list[dict]
    status: str
    auto_cancel_after_sec: Optional[int] = None
    gemini_reason: Optional[str] = None


class HoldRequest(BaseModel):
    txn_id: str
    risk_score: int
    sender_phone: str = "unknown"
    transaction_amount: float = 0.0
    reason: Optional[str] = None


class HoldResponse(BaseModel):
    txn_id: str
    status: str
    message: str
    auto_cancel_after_sec: Optional[int] = None


class CaregiverAlert(BaseModel):
    txn_id: str
    risk_score: int
    sender_phone: str = "unknown"
    transaction_amount: float = 0.0
    reason: str = ""
    timestamp: float = 0.0
    status: str = "pending"
    transcript: Optional[str] = None
    translation: Optional[str] = None


class ActionResponse(BaseModel):
    txn_id: str
    action: str
    message: str


class TransactionRecord(BaseModel):
    txn_id: str
    sender_phone: str
    transcript: str
    translation: Optional[str] = None
    risk_score: int
    risk_factors: list[dict] = []
    is_new_payee: bool = False
    transaction_amount: float = 0.0
    status: str = "pending"
    timestamp: float = 0.0
    gemini_reason: Optional[str] = None

    def model_dump_redis(self) -> dict:
        """Serialize for Redis HSET (all values must be strings)."""
        d = self.model_dump()
        d["risk_factors"] = json.dumps(d["risk_factors"])
        d["is_new_payee"] = str(d["is_new_payee"])
        d["transaction_amount"] = str(d["transaction_amount"])
        d["risk_score"] = str(d["risk_score"])
        d["timestamp"] = str(d["timestamp"])
        return d
