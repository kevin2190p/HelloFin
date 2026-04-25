"""
LLM Analyzer – Qwen3 Scam Text Analysis via Groq
==================================================
Uses Qwen3-32B (via Groq) to perform deep semantic analysis on
transcribed voice notes and text messages from the scammer.

Detects:
  - Social engineering tactics
  - Authority impersonation
  - Urgency/fear manipulation
  - Financial fraud patterns
  - Malay + English + Manglish phishing signals

Returns structured JSON: risk_score, flags, explanation, severity.
"""

import json
import os

import httpx
import structlog

logger = structlog.get_logger("hellofin.llm_analyzer")

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are HelloFin's elite voice phishing detection AI for Malaysia.
Your job is to analyze messages (transcribed voice notes or texts) and detect scam/phishing attempts.

Malaysian scam patterns to detect:
1. AUTHORITY IMPERSONATION: Pretending to be Bank Negara, PDRM, LHDN, Polis, Immigration, MACC, Mahkamah, Telco, Bank staff
2. URGENCY/FEAR TACTICS: "transfer sekarang", "akaun akan dibekukan", "waran tangkap", "anda akan ditangkap"
3. FINANCIAL EXTRACTION: Requesting OTP, TAC, bank account, PIN, "akaun selamat", "transfer to safe account"
4. EMOTIONAL MANIPULATION: Family emergency, accident, kidnapping, hospital
5. LOVE SCAMS: Excessive flattery, requests for money from "strangers"
6. INVESTMENT SCAMS: Guaranteed returns, crypto, "unit trust", "high yield"
7. PARCEL SCAMS: "Bungkusan anda mengandungi dadah", customs, Pos Malaysia
8. MACAU SCAM: Multi-layered impersonation (police + bank + court)

Respond ONLY with valid JSON in this exact format:
{
  "is_scam": true/false,
  "confidence": 0-100,
  "scam_type": "authority_impersonation|financial_extraction|love_scam|investment_scam|parcel_scam|macau_scam|unknown",
  "risk_score": 0-100,
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "detected_tactics": ["list", "of", "specific", "tactics"],
  "flagged_phrases": ["exact phrases from the text that are suspicious"],
  "explanation": "Brief explanation in English of why this is/isn't a scam",
  "recommendation": "What the victim should do",
  "language_detected": "malay|english|manglish|mandarin|mixed"
}"""


async def analyze_with_qwen(text: str, sender_phone: str = "unknown") -> dict:
    """
    Analyze a message using Qwen3 for deep scam detection.

    Args:
        text: The message text (transcription or raw text).
        sender_phone: Sender's phone number for context.

    Returns:
        Analysis dict with risk_score, flags, explanation.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key.startswith("REPLACE"):
        logger.warning("qwen_skipped", reason="GROQ_API_KEY not configured")
        return _fallback_response()

    user_message = f"""Analyze this message from phone number +{sender_phone}:

---
{text}
---

Is this a scam/phishing attempt? Provide your analysis as JSON."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama3-70b-8192",  # More stable Llama 3 model
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.1,  # Low temp for deterministic detection
                    "max_tokens": 1024,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()

        raw = resp.json()["choices"][0]["message"]["content"]
        analysis = json.loads(raw)

        logger.info(
            "qwen_analysis_done",
            sender=sender_phone,
            is_scam=analysis.get("is_scam"),
            confidence=analysis.get("confidence"),
            scam_type=analysis.get("scam_type"),
            risk_score=analysis.get("risk_score"),
        )
        return analysis

    except json.JSONDecodeError as e:
        logger.error("qwen_json_parse_error", error=str(e))
        return _fallback_response()
    except Exception as e:
        logger.error("qwen_api_error", error=str(e))
        return _fallback_response()


def _fallback_response() -> dict:
    """Return a neutral response when LLM is unavailable."""
    return {
        "is_scam": False,
        "confidence": 0,
        "scam_type": "unknown",
        "risk_score": 0,
        "severity": "LOW",
        "detected_tactics": [],
        "flagged_phrases": [],
        "explanation": "LLM analysis unavailable – keyword engine used only.",
        "recommendation": "Proceed with keyword-based scoring only.",
        "language_detected": "unknown",
    }
