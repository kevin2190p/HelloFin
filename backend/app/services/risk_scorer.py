"""
Risk Scorer – Voice Phishing Detection Engine
==============================================
Multi-factor risk scoring for Malaysian voice phishing:
  - Keyword / phrase detection (BM + EN)
  - Urgency regex patterns
  - Authority impersonation detection
  - International / unknown caller flag
  - New payee flag
  - Transaction amount threshold

Score range: 0–100 (≥80 = HIGH, ≥50 = MEDIUM, <50 = LOW)
"""

import os
import re
from typing import Optional

import structlog

logger = structlog.get_logger("hellofin.risk_scorer")

# ────────────────────────────────────────────────────────────
# KEYWORD DICTIONARIES (weighted by severity)
# ────────────────────────────────────────────────────────────

# Authority impersonation phrases (high weight: 20 pts each)
AUTHORITY_KEYWORDS = [
    "bank negara",
    "polis diraja",
    "royal malaysia police",
    "jabatan imigresen",
    "immigration department",
    "lhdn",
    "inland revenue",
    "suruhanjaya",
    "mahkamah",
    "court order",
    "interpol",
    "bnm",
    "securities commission",
    "sprm",
    "macc",
    "anti-corruption",
    "kastam",
    "customs department",
    "pdrm",
    "kementerian",
    "ministry of",
]

# Urgency / threat phrases (medium weight: 15 pts each)
URGENCY_KEYWORDS = [
    "transfer now",
    "transfer sekarang",
    "immediately",
    "segera",
    "urgent",
    "within 24 hours",
    "dalam 24 jam",
    "arrest warrant",
    "waran tangkap",
    "your account will be frozen",
    "akaun anda akan dibekukan",
    "money laundering",
    "pengubahan wang haram",
    "you will be arrested",
    "anda akan ditangkap",
    "do not tell anyone",
    "jangan beritahu sesiapa",
    "keep this confidential",
    "rahsia",
    "time is running out",
    "masa semakin singkat",
    "last chance",
    "peluang terakhir",
    "penalty",
    "denda",
    "blacklisted",
    "disenarai hitam",
    "suspend",
    "gantung",
]

# Financial instruction phrases (medium weight: 12 pts each)
FINANCIAL_KEYWORDS = [
    "transfer to this account",
    "pindahkan ke akaun ini",
    "safe account",
    "akaun selamat",
    "verification account",
    "akaun pengesahan",
    "temporary hold",
    "tac number",
    "nombor tac",
    "otp",
    "pin number",
    "nombor pin",
    "credit card number",
    "nombor kad kredit",
    "bank account number",
    "nombor akaun bank",
    "give me your",
    "berikan saya",
    "send money",
    "hantar duit",
    "wire transfer",
    "western union",
    "cryptocurrency",
    "bitcoin",
    "gift card",
    "reload card",
]

# Emotional manipulation (low weight: 8 pts each)
EMOTIONAL_KEYWORDS = [
    "your family",
    "keluarga anda",
    "your children",
    "anak-anak anda",
    "accident",
    "kemalangan",
    "hospital",
    "emergency",
    "kecemasan",
    "kidnap",
    "culik",
    "ransom",
    "wang tebusan",
    "help me",
    "tolong saya",
    "i am a victim",
    "saya mangsa",
]

# ────────────────────────────────────────────────────────────
# REGEX PATTERNS
# ────────────────────────────────────────────────────────────

URGENCY_PATTERNS = [
    re.compile(r"within\s+\d+\s*(hours?|minutes?|jam|minit)", re.IGNORECASE),
    re.compile(r"dalam\s+\d+\s*(jam|minit|hari)", re.IGNORECASE),
    re.compile(r"before\s+\d{1,2}[:.]\d{2}", re.IGNORECASE),
    re.compile(r"sebelum\s+\d{1,2}[:.]\d{2}", re.IGNORECASE),
    re.compile(r"deadline", re.IGNORECASE),
    re.compile(r"dateline", re.IGNORECASE),  # Common Malaysian English variant
]

# International number patterns (non-Malaysian)
INTL_NUMBER_PATTERN = re.compile(r"^\+(?!60)\d{7,15}$")
UNKNOWN_NUMBER_INDICATORS = ["unknown", "private", "withheld", "no caller id"]


def calculate_risk_score(
    transcript: str,
    caller_number: str = "unknown",
    is_new_payee: bool = False,
    transaction_amount: float = 0.0,
) -> dict:
    """
    Calculate a comprehensive phishing risk score.

    Args:
        transcript: Transcribed voice note text.
        caller_number: Phone number of the caller.
        is_new_payee: Whether the transfer target is a new/unknown payee.
        transaction_amount: Amount in MYR.

    Returns:
        Dictionary with risk_score, risk_level, risk_factors, recommendation.
    """
    score = 0
    factors = []
    transcript_lower = transcript.lower()

    # ── 1. Authority impersonation (20 pts each, max 40) ───
    authority_hits = [
        kw for kw in AUTHORITY_KEYWORDS if kw in transcript_lower
    ]
    if authority_hits:
        pts = min(len(authority_hits) * 20, 40)
        score += pts
        factors.append({
            "category": "authority_impersonation",
            "points": pts,
            "matches": authority_hits[:5],
            "description": "Caller impersonates government/financial authority",
        })

    # ── 2. Urgency / threat phrases (15 pts each, max 30) ──
    urgency_hits = [
        kw for kw in URGENCY_KEYWORDS if kw in transcript_lower
    ]
    if urgency_hits:
        pts = min(len(urgency_hits) * 15, 30)
        score += pts
        factors.append({
            "category": "urgency_pressure",
            "points": pts,
            "matches": urgency_hits[:5],
            "description": "High-pressure urgency tactics detected",
        })

    # ── 3. Financial instruction phrases (12 pts each, max 24) ─
    financial_hits = [
        kw for kw in FINANCIAL_KEYWORDS if kw in transcript_lower
    ]
    if financial_hits:
        pts = min(len(financial_hits) * 12, 24)
        score += pts
        factors.append({
            "category": "financial_instruction",
            "points": pts,
            "matches": financial_hits[:5],
            "description": "Suspicious financial instructions detected",
        })

    # ── 4. Emotional manipulation (8 pts each, max 16) ─────
    emotional_hits = [
        kw for kw in EMOTIONAL_KEYWORDS if kw in transcript_lower
    ]
    if emotional_hits:
        pts = min(len(emotional_hits) * 8, 16)
        score += pts
        factors.append({
            "category": "emotional_manipulation",
            "points": pts,
            "matches": emotional_hits[:5],
            "description": "Emotional manipulation tactics detected",
        })

    # ── 5. Urgency regex patterns (5 pts each, max 10) ─────
    regex_hits = [
        p.pattern for p in URGENCY_PATTERNS if p.search(transcript_lower)
    ]
    if regex_hits:
        pts = min(len(regex_hits) * 5, 10)
        score += pts
        factors.append({
            "category": "urgency_pattern",
            "points": pts,
            "matches": regex_hits[:3],
            "description": "Time-pressure patterns detected",
        })

    # ── 6. International / unknown caller (+10) ────────────
    is_intl = INTL_NUMBER_PATTERN.match(caller_number)
    is_unknown = caller_number.lower() in UNKNOWN_NUMBER_INDICATORS
    if is_intl or is_unknown:
        score += 10
        factors.append({
            "category": "suspicious_caller",
            "points": 10,
            "matches": [caller_number],
            "description": "International or unknown caller number",
        })

    # ── 7. New payee flag (+10) ────────────────────────────
    if is_new_payee:
        score += 10
        factors.append({
            "category": "new_payee",
            "points": 10,
            "matches": ["new_payee=true"],
            "description": "Transfer to a new/unknown payee",
        })

    # ── 8. High transaction amount (+5 if > RM1000) ───────
    if transaction_amount > 1000:
        score += 5
        factors.append({
            "category": "high_amount",
            "points": 5,
            "matches": [f"RM {transaction_amount:,.2f}"],
            "description": f"Transaction amount exceeds RM 1,000",
        })

    # ── Clamp score to 0–100 ──────────────────────────────
    score = min(score, 100)

    # ── Determine level and recommendation ────────────────
    threshold_high = int(os.getenv("RISK_THRESHOLD_HIGH", "80"))
    threshold_med = int(os.getenv("RISK_THRESHOLD_MEDIUM", "50"))

    if score >= threshold_high:
        level = "HIGH"
        recommendation = (
            "HOLD TRANSACTION. Likely voice phishing attempt. "
            "Notify caregiver immediately. Auto-cancel in 10 minutes "
            "if no verification."
        )
    elif score >= threshold_med:
        level = "MEDIUM"
        recommendation = (
            "FLAG for review. Suspicious patterns detected. "
            "Request additional verification before proceeding."
        )
    else:
        level = "LOW"
        recommendation = (
            "Transaction appears safe. Continue with standard processing."
        )

    logger.info(
        "risk_calculated",
        score=score,
        level=level,
        factor_count=len(factors),
    )

    return {
        "risk_score": score,
        "risk_level": level,
        "risk_factors": factors,
        "recommendation": recommendation,
    }
