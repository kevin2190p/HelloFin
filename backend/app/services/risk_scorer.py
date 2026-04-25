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

# ── Section 1: Authority Impersonation (15-20 pts each) ──
AUTHORITY_KEYWORDS = [
    "bank negara", "bnm", "lhdn", "inland revenue",
    "pdrm", "polis diraja", "royal malaysia police", "bukit aman",
    "nsrc", "national scam response", "ccid", "commercial crime",
    "kastam", "customs department", "customs", "jabatan kastam",
    "sprm", "macc", "anti-corruption",
    "tnb", "tenaga nasional",
    "mybayar", "jpj",
    "suruhanjaya", "mahkamah", "court order", "interpol",
    "securities commission", "kementerian", "ministry of",
    "jabatan imigresen", "immigration department",
    "sergeant", "inspector", "officer", "pegawai",
    "bank negara malaysia", "police fraud department",
]

# ── Section 2: Urgency & Legal Threats (10-25 pts each) ──
URGENCY_KEYWORDS = [
    "arrest warrant", "warrant of arrest", "waran tangkap",
    "urgent", "immediately", "right now", "segera",
    "last warning", "final warning", "amaran terakhir",
    "do not hang up", "jangan tutup telefon",
    "keep this confidential", "don't tell anyone", "do not tell anyone",
    "jangan beritahu sesiapa", "rahsia", "confidential",
    "under investigation", "sedang disiasat",
    "money laundering", "pengubahan wang haram",
    "freeze your account", "account will be blocked",
    "akaun anda akan dibekukan",
    "legal action", "court case", "tindakan undang-undang",
    "pemotongan bekalan", "supply cut-off",
    "you will be arrested", "anda akan ditangkap",
    "transfer now", "transfer sekarang",
    "within 24 hours", "dalam 24 jam",
    "time is running out", "masa semakin singkat",
    "last chance", "peluang terakhir", "only chance",
    "penalty", "denda", "blacklisted", "disenarai hitam",
    "suspend", "gantung",
    "failure to comply", "cooperate fully",
    "immediate", "escalate",
]

# ── Section 3: Parcel & Logistics Scams (12-15 pts each) ──
PARCEL_KEYWORDS = [
    "parcel", "courier", "pos laju", "pos malaysia",
    "prohibited items", "illegal items", "barang terlarang",
    "detained by customs", "customs hold", "ditahan",
    "claim your parcel", "redeem your goods",
    "unpaid packages", "incomplete payment",
    "package delivery", "failed delivery",
    "returned to sender", "penalty fee",
]

# ── Section 4: Banking & Financial Credentials (20-25 pts each) ──
FINANCIAL_KEYWORDS = [
    "tac", "transaction authorisation code", "nombor tac",
    "otp", "one time password",
    "safe account", "secure account", "akaun selamat",
    "transfer to this account", "pindahkan ke akaun",
    "internet banking", "online banking",
    "atm card", "pin number", "nombor pin", "card number",
    "mule account", "akaun keldai",
    "bank account compromised", "unauthorised transaction",
    "credit card number", "nombor kad kredit",
    "bank account number", "nombor akaun bank",
    "give me your", "berikan saya",
    "send money", "hantar duit", "wire transfer",
    "western union", "cryptocurrency", "bitcoin",
    "gift card", "reload card",
    "transfer funds", "verification account",
    "akaun pengesahan", "maybank", "cimb", "rhb",
    "corporate account",
]

# ── Section 5: Fake Emergency & Family Scams (15-20 pts each) ──
EMOTIONAL_KEYWORDS = [
    "using a friend's phone", "friend's phone",
    "my phone is dead", "phone rosak", "phone is dead",
    "emergency", "accident", "hospital", "kecemasan", "kemalangan",
    "don't call my number", "don't call my phone",
    "jangan call", "borrowed phone",
    "ai voice", "deepfake",
    "your family", "keluarga anda",
    "your children", "anak-anak anda",
    "kidnap", "culik", "ransom", "wang tebusan",
    "help me", "tolong saya", "i'm in trouble", "in bad trouble",
    "i am a victim", "saya mangsa",
    "wallet got stolen", "wallet at work",
]

# ── Section 6: Investment & Job Scams (10-15 pts each) ──
INVESTMENT_KEYWORDS = [
    "high return", "guaranteed return", "guaranteed returns",
    "10% return", "profit", "returns every",
    "work from home", "part-time job", "part time job",
    "cryptocurrency", "crypto", "forex",
    "processing fee", "service fee", "registration fee",
    "investment alert", "0% risk", "no hidden fees",
    "withdraw anytime", "daily commission",
    "rm8,000", "rm15,000", "rm23,000",
    "vip group", "join our",
    "shopee", "lazada", "tiktok",
    "simple tasks", "no experience needed",
    "starter bonus",
]

# ── Section 7: Malware & Phishing Links (15-20 pts each) ──
PHISHING_KEYWORDS = [
    "click this link", "click the link", "click here",
    "apk", "download this app",
    "verify your account", "verification code",
    "update your information", "update your profile",
    "do not share this code",
    "copy code",
]

# ── Section 8: Financial Aid & Prize Scams (10 pts each) ──
PRIZE_KEYWORDS = [
    "bantuan ramadan", "government aid",
    "you have won", "cash prize", "congratulations",
    "claim your prize", "redeem your gift",
    "str", "sumbangan tunai rahmah",
    "your number has been selected",
    "forward this to",
    "urgent reply needed",
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
    re.compile(r"dateline", re.IGNORECASE),
    re.compile(r"rm\s*\d{1,3}(,\d{3})+", re.IGNORECASE),  # Large RM amounts
    re.compile(r"\.(xyz|top|club|online|buzz)\b", re.IGNORECASE),  # Suspicious domains
    re.compile(r"bit\.ly|tinyurl|shorturl", re.IGNORECASE),  # URL shorteners
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

    # ── 1. Authority impersonation (15 pts each, max 45) ───
    authority_hits = [kw for kw in AUTHORITY_KEYWORDS if kw in transcript_lower]
    if authority_hits:
        pts = min(len(authority_hits) * 15, 45)
        score += pts
        factors.append({"category": "authority_impersonation", "points": pts, "matches": authority_hits[:5],
            "description": "Caller impersonates government/financial authority"})

    # ── 2. Urgency / threat phrases (10 pts each, max 35) ──
    urgency_hits = [kw for kw in URGENCY_KEYWORDS if kw in transcript_lower]
    if urgency_hits:
        pts = min(len(urgency_hits) * 10, 35)
        score += pts
        factors.append({"category": "urgency_pressure", "points": pts, "matches": urgency_hits[:5],
            "description": "High-pressure urgency tactics detected"})

    # ── 3. Parcel & logistics scams (12 pts each, max 24) ──
    parcel_hits = [kw for kw in PARCEL_KEYWORDS if kw in transcript_lower]
    if parcel_hits:
        pts = min(len(parcel_hits) * 12, 24)
        score += pts
        factors.append({"category": "parcel_scam", "points": pts, "matches": parcel_hits[:5],
            "description": "Parcel/logistics scam patterns detected"})

    # ── 4. Financial credential theft (20 pts each, max 40) ─
    financial_hits = [kw for kw in FINANCIAL_KEYWORDS if kw in transcript_lower]
    if financial_hits:
        pts = min(len(financial_hits) * 20, 40)
        score += pts
        factors.append({"category": "financial_credential", "points": pts, "matches": financial_hits[:5],
            "description": "Financial credential theft attempt detected"})

    # ── 5. Emotional / family emergency (15 pts each, max 30) ─
    emotional_hits = [kw for kw in EMOTIONAL_KEYWORDS if kw in transcript_lower]
    if emotional_hits:
        pts = min(len(emotional_hits) * 15, 30)
        score += pts
        factors.append({"category": "emergency_scam", "points": pts, "matches": emotional_hits[:5],
            "description": "Fake emergency / family scam patterns"})

    # ── 6. Investment & job scams (10 pts each, max 25) ────
    invest_hits = [kw for kw in INVESTMENT_KEYWORDS if kw in transcript_lower]
    if invest_hits:
        pts = min(len(invest_hits) * 10, 25)
        score += pts
        factors.append({"category": "investment_scam", "points": pts, "matches": invest_hits[:5],
            "description": "Investment/job scam patterns detected"})

    # ── 7. Phishing links (15 pts each, max 25) ───────────
    phish_hits = [kw for kw in PHISHING_KEYWORDS if kw in transcript_lower]
    if phish_hits:
        pts = min(len(phish_hits) * 15, 25)
        score += pts
        factors.append({"category": "phishing_link", "points": pts, "matches": phish_hits[:5],
            "description": "Phishing link / malware patterns detected"})

    # ── 8. Prize / aid scams (10 pts each, max 20) ────────
    prize_hits = [kw for kw in PRIZE_KEYWORDS if kw in transcript_lower]
    if prize_hits:
        pts = min(len(prize_hits) * 10, 20)
        score += pts
        factors.append({"category": "prize_scam", "points": pts, "matches": prize_hits[:5],
            "description": "Prize/financial aid scam patterns detected"})

    # ── 9. Urgency regex patterns (5 pts each, max 15) ────
    regex_hits = [p.pattern for p in URGENCY_PATTERNS if p.search(transcript_lower)]
    if regex_hits:
        pts = min(len(regex_hits) * 5, 15)
        score += pts
        factors.append({"category": "urgency_pattern", "points": pts, "matches": regex_hits[:3],
            "description": "Time-pressure / suspicious patterns detected"})

    # ── 10. Behavioral: multi-authority + isolation (+15-25) ─
    if len(authority_hits) >= 2:
        score += 15
        factors.append({"category": "multi_authority", "points": 15, "matches": authority_hits[:3],
            "description": "Multiple authority names = classic Macau Scam"})
    isolation_phrases = ["don't tell anyone", "do not tell anyone", "jangan beritahu", "keep this confidential", "don't call my"]
    if any(p in transcript_lower for p in isolation_phrases):
        score += 20
        factors.append({"category": "isolation_tactic", "points": 20, "matches": ["isolation detected"],
            "description": "Victim isolation tactic detected"})

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
