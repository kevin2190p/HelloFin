"""
AWS Bedrock Analyzer – Claude 3 Haiku Scam Detection
=====================================================
Uses AWS Bedrock (Anthropic Claude 3 Haiku) for English-leaning
scam analysis. Pairs with Alibaba DashScope Qwen for Mandarin/Malay
to form a dual-LLM cross-validation layer.

This is the AWS half of Fakeout's multi-cloud risk-scoring strategy.
"""

import asyncio
import json
import os

import structlog

logger = structlog.get_logger("fakeout.aws_bedrock")

DEFAULT_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
DEFAULT_REGION = "ap-southeast-1"  # Singapore – Bedrock available

SYSTEM_PROMPT = """You are Fakeout's English-language scam-detection expert.
Analyze the message for Malaysian voice-phishing patterns:
authority impersonation (PDRM/LHDN/Bank Negara), urgency, OTP/TAC requests,
parcel scams, investment scams, Macau scam, family-emergency scams.

Respond with ONLY valid JSON, no prose:
{
  "risk_score": 0-100,
  "is_scam": true|false,
  "confidence": 0-100,
  "scam_type": "authority_impersonation|financial_extraction|love_scam|investment_scam|parcel_scam|macau_scam|family_emergency|unknown",
  "flagged_phrases": ["..."],
  "explanation": "one short sentence",
  "language_detected": "english|malay|manglish|mandarin|mixed"
}"""


def _fallback() -> dict:
    return {
        "risk_score": 0,
        "is_scam": False,
        "confidence": 0,
        "scam_type": "unknown",
        "flagged_phrases": [],
        "explanation": "AWS Bedrock unavailable.",
        "language_detected": "unknown",
        "provider": "aws_bedrock",
        "status": "skipped",
    }


def _invoke_bedrock_sync(text: str, sender_phone: str) -> dict:
    """Synchronous Bedrock call (run inside a thread executor)."""
    ak = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    if not ak or ak.startswith("REPLACE"):
        return _fallback()

    try:
        import boto3  # boto3 already in requirements.txt
    except ImportError:
        logger.error("boto3_missing")
        return _fallback()

    try:
        # Support both permanent IAM keys AND temporary STS/SSO creds
        # (SSO users will have AWS_SESSION_TOKEN; permanent IAM users won't).
        client_kwargs = {
            "aws_access_key_id": ak,
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "region_name": os.getenv("AWS_BEDROCK_REGION", DEFAULT_REGION),
        }
        session_token = os.getenv("AWS_SESSION_TOKEN", "").strip()
        if session_token and not session_token.startswith("REPLACE"):
            client_kwargs["aws_session_token"] = session_token
        client = boto3.client("bedrock-runtime", **client_kwargs)
        model_id = os.getenv("AWS_BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "temperature": 0.2,
            "system": SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Phone +{sender_phone}. Message:\n---\n{text}\n---\n"
                        "Return JSON only."
                    ),
                }
            ],
        }

        resp = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        payload = json.loads(resp["body"].read().decode())
        # Claude on Bedrock returns {"content":[{"type":"text","text":"..."}]}
        text_out = payload.get("content", [{}])[0].get("text", "{}")
        # Strip markdown fencing if Claude added it
        text_out = text_out.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        analysis = json.loads(text_out)
        analysis["provider"] = "aws_bedrock"
        analysis["status"] = "ok"
        analysis["model"] = model_id
        return analysis
    except json.JSONDecodeError as e:
        logger.error("bedrock_json_parse_error", error=str(e))
        out = _fallback()
        out["status"] = "parse_error"
        return out
    except Exception as e:
        logger.error("bedrock_api_error", error=str(e))
        out = _fallback()
        out["status"] = "error"
        out["error"] = str(e)
        return out


async def analyze_with_bedrock(text: str, sender_phone: str = "unknown") -> dict:
    """
    Async wrapper – runs the boto3 sync call in a thread so it doesn't
    block FastAPI's event loop. Mirrors the Qwen analyzer signature.
    """
    if not text:
        return _fallback()
    result = await asyncio.to_thread(_invoke_bedrock_sync, text, sender_phone)
    logger.info(
        "bedrock_analysis_done",
        sender=sender_phone,
        risk_score=result.get("risk_score"),
        scam_type=result.get("scam_type"),
        status=result.get("status"),
    )
    return result
