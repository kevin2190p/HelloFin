"""
Risk Scorer – Advanced Keyword & Pattern Matching Engine
=========================================================
Implements the 8-section professional scam detection table with specific weights.
"""

import structlog

logger = structlog.get_logger("hellofin.risk_scorer")

# Define the tables with their categories
SCAM_TABLES = {
    "Section 1: Authority Impersonation": {
        "bank negara": 15, "lhdn": 15, "pdrm": 15, "bukit aman": 15, "police": 15,
        "nsrc": 20, "ccid": 20, "commercial crime": 20, "customs": 15, "kastam": 15,
        "sprm": 15, "macc": 15, "tnb": 15, "tenaga nasional": 15, "mybayar": 15,
    },
    "Section 2: Urgency & Legal Threats": {
        "arrest warrant": 25, "warrant of arrest": 25, "waran tangkap": 25,
        "urgent": 10, "immediately": 10, "right now": 10, "as fast as possible": 15,
        "last warning": 15, "final warning": 15, "do not hang up": 15,
        "keep this confidential": 20, "don't tell anyone": 20, "jangan beritahu": 20,
        "under investigation": 15, "money laundering": 20, "freeze your account": 15,
        "account will be blocked": 15, "legal action": 10, "court case": 10,
        "pemotongan bekalan": 10, "tindakan undang-undang": 10,
    },
    "Section 3: Parcel & Logistics Scams": {
        "parcel": 12, "courier": 12, "pos laju": 12, "prohibited items": 15,
        "illegal items": 15, "detained by customs": 15, "customs hold": 15,
        "claim your parcel": 12, "redeem your goods": 12,
    },
    "Section 4: Banking & Financial Credentials": {
        "tac": 25, "otp": 25, "one time password": 25, "transfer to safe account": 20,
        "secure account": 20, "akaun selamat": 20, "internet banking": 20,
        "online banking access": 20, "atm card": 20, "pin": 20, "card number": 20,
        "mule account": 25, "akaun keldai": 25, "bank account compromised": 15,
        "unauthorised transaction": 15,
    },
    "Section 5: Fake Emergency & Family Scams": {
        "friend's phone": 15, "phone is dead": 15, "rosak": 15, "emergency": 20,
        "accident": 20, "hospital": 20, "don't call my number": 20, "ai voice": 15, "deepfake": 15,
    },
    "Section 6: Investment & Job Scams": {
        "high return": 15, "guaranteed return": 15, "10% returns": 15,
        "work from home": 10, "part-time job": 10, "cryptocurrency": 10,
        "crypto": 10, "forex": 10, "processing fee": 15, "service fee": 15,
    },
    "Section 7: Malware & Phishing Links": {
        "click this link": 15, "apk": 20, "download this app": 20,
        "verify your account": 15, "update your information": 12, "update your profile": 12,
    },
    "Section 8: Financial Aid & Prize Scams": {
        "bantuan ramadan": 10, "government aid": 10, "you have won": 10,
        "cash prize": 10, "claim your prize": 10, "redeem your gift": 10,
        "str": 10, "sumbangan tunai rahmah": 10,
    }
}

def calculate_risk_score(transcript: str, **kwargs) -> dict:
    """
    Calculate risk score based on the 8-section professional table.
    """
    if not transcript:
        return {"risk_score": 0, "risk_level": "LOW", "risk_factors": []}

    transcript_lower = transcript.lower()
    score = 0
    factors = []

    for section, table in SCAM_TABLES.items():
        hits = []
        section_points = 0
        for kw, weight in table.items():
            if kw in transcript_lower:
                section_points += weight
                hits.append(kw)
        
        if hits:
            score += section_points
            factors.append({
                "category": section,
                "points": section_points,
                "matches": hits
            })

    # Normalization & Thresholds
    final_score = min(100, score)
    
    level = "LOW"
    if final_score >= 80: level = "CRITICAL"
    elif final_score >= 50: level = "HIGH"
    elif final_score >= 30: level = "MEDIUM"

    return {
        "risk_score": final_score,
        "risk_level": level,
        "risk_factors": factors,
        "recommendation": "Block and report this caller immediately." if final_score >= 50 else "Proceed with caution."
    }
