"""
Alibaba DashScope (Qwen) Analyzer – Mandarin/Malay Scam Detection
==================================================================
Calls Alibaba Cloud Model Studio (DashScope) Qwen-Turbo via the
OpenAI-compatible endpoint. Pairs with AWS Bedrock Claude to form
Fakeout's dual-LLM cross-validation layer.

Why Alibaba for this role?
  - Qwen is best-in-class for Mandarin and SE-Asian languages.
  - Inference runs in APAC for data residency.
  - If AWS and Alibaba disagree on the score, we escalate to caregiver.

This is the Alibaba Cloud half of Fakeout's multi-cloud strategy.
"""

import json
import os

import httpx
import structlog

logger = structlog.get_logger("fakeout.alibaba_qwen")

# OpenAI-compatible endpoint (Singapore region for APAC residency).
# Switch host to https://dashscope.aliyuncs.com/compatible-mode/v1 for Mainland.
DASHSCOPE_URL = os.getenv(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
).rstrip("/") + "/chat/completions"

DEFAULT_MODEL = "qwen-turbo"

SYSTEM_PROMPT = """你是 Fakeout 的多语种诈骗检测专家 / You are Fakeout's multilingual scam-detection expert.
Detect Malaysian voice-phishing patterns in Mandarin, Bahasa Malaysia, English, or Manglish:
authority impersonation (PDRM/LHDN/Bank Negara/警察/银行), urgency, OTP/TAC requests,
parcel scams, investment scams, Macau scam (澳门骗局), family-emergency scams.

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
        "explanation": "Alibaba DashScope unavailable.",
        "language_detected": "unknown",
        "provider": "alibaba_dashscope",
        "status": "skipped",
    }


async def analyze_with_dashscope(text: str, sender_phone: str = "unknown") -> dict:
    """
    Analyze a message using Alibaba Qwen via DashScope OpenAI-compatible API.
    """
    if not text:
        return _fallback()

    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key or api_key.startswith("REPLACE"):
        logger.warning("dashscope_skipped", reason="DASHSCOPE_API_KEY not configured")
        return _fallback()

    model = os.getenv("DASHSCOPE_MODEL", DEFAULT_MODEL)
    user_message = (
        f"Phone +{sender_phone}. Message:\n---\n{text}\n---\nReturn JSON only."
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                DASHSCOPE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()

        raw = resp.json()["choices"][0]["message"]["content"]
        # Strip any accidental fencing
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        analysis = json.loads(raw)
        analysis["provider"] = "alibaba_dashscope"
        analysis["status"] = "ok"
        analysis["model"] = model
        logger.info(
            "dashscope_analysis_done",
            sender=sender_phone,
            risk_score=analysis.get("risk_score"),
            scam_type=analysis.get("scam_type"),
            language=analysis.get("language_detected"),
        )
        return analysis

    except json.JSONDecodeError as e:
        logger.error("dashscope_json_parse_error", error=str(e))
        out = _fallback()
        out["status"] = "parse_error"
        return out
    except Exception as e:
        logger.error("dashscope_api_error", error=str(e))
        out = _fallback()
        out["status"] = "error"
        out["error"] = str(e)
        return out
