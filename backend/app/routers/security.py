"""
Security Router – Cross-Cloud KMS Envelope Encryption Demo
============================================================
Endpoints:
  POST /security/encrypt   – encrypt arbitrary text with AWS+Alibaba KMS
  POST /security/decrypt   – decrypt a previously produced envelope
  POST /security/round-trip – self-test: encrypt then decrypt sample PII
  GET  /security/keys      – returns which KMS keys are configured

These endpoints exist so judges can SEE the cross-cloud guarantee
end-to-end during the live demo.
"""

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.multicloud_crypto import (
    SCHEME_VERSION,
    decrypt_payload,
    encrypt_payload,
)

logger = structlog.get_logger("fakeout.security")
router = APIRouter()


# ---------- request / response models ----------
class EncryptRequest(BaseModel):
    plaintext: str = Field(..., description="UTF-8 text to encrypt")
    aad: Optional[str] = Field(
        None, description="Optional additional authenticated data (string)."
    )


class EnvelopeBlob(BaseModel):
    scheme: str
    oss_object_key: str
    oss_bucket: str
    nonce: str
    ciphertext: str
    aws_key_id: str
    alibaba_key_id: str


class DecryptRequest(EnvelopeBlob):
    aad: Optional[str] = None


class DecryptResponse(BaseModel):
    plaintext: str


# ---------- endpoints ----------
@router.get("/keys")
async def list_keys():
    """Show which KMS keys / regions are configured (no secrets exposed)."""
    import os
    return {
        "scheme": SCHEME_VERSION,
        "aws_kms_key_id": os.getenv("AWS_KMS_KEY_ID", "<not set>"),
        "aws_kms_region": os.getenv("AWS_KMS_REGION") or os.getenv("AWS_BEDROCK_REGION") or "ap-southeast-1",
        "alibaba_kms_key_id": os.getenv("ALIBABA_KMS_KEY_ID", "<not set>"),
        "alibaba_kms_region": os.getenv("ALIBABA_KMS_REGION", "ap-southeast-1"),
    }


@router.post("/encrypt", response_model=EnvelopeBlob)
async def encrypt(req: EncryptRequest):
    aad_bytes = req.aad.encode("utf-8") if req.aad else None
    try:
        blob = await encrypt_payload(req.plaintext.encode("utf-8"), aad=aad_bytes)
        return EnvelopeBlob(**blob)
    except Exception as e:
        logger.error("encrypt_endpoint_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decrypt", response_model=DecryptResponse)
async def decrypt(req: DecryptRequest):
    aad_bytes = req.aad.encode("utf-8") if req.aad else None
    blob = req.model_dump(exclude={"aad"})
    try:
        pt = await decrypt_payload(blob, aad=aad_bytes)
        return DecryptResponse(plaintext=pt.decode("utf-8"))
    except Exception as e:
        logger.error("decrypt_endpoint_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/round-trip")
async def round_trip():
    """
    Self-test: encrypt a sample of fake PII then decrypt it.
    Produces a clean log trail that demonstrates BOTH clouds were touched.
    """
    sample = (
        "Fakeout sensitive PII | "
        "victim_name='Aunty Lim' card='4111-1111-1111-1234' "
        "otp='999888' transcript='Macau scam intercept'"
    )
    aad = b"fakeout-finhack-2026"
    try:
        blob = await encrypt_payload(sample.encode("utf-8"), aad=aad)
        recovered = await decrypt_payload(blob, aad=aad)
        ok = recovered.decode("utf-8") == sample
        return {
            "status": "ok" if ok else "mismatch",
            "scheme": blob["scheme"],
            "aws_key_id": blob["aws_key_id"],
            "alibaba_key_id": blob["alibaba_key_id"],
            "ciphertext_bytes": len(blob["ciphertext"]),
            "oss_bucket": blob["oss_bucket"],
            "oss_object_key": blob["oss_object_key"],
            "nonce": blob["nonce"],
            "round_trip_match": ok,
            "providers_required_to_decrypt": [
                "AWS KMS (Decrypt the wrapped DEK)",
                "Alibaba OSS + KMS (download SSE-KMS-encrypted object)",
            ],
        }
    except Exception as e:
        logger.error("round_trip_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
