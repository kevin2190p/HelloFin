"""
Risk Explainer – Groq-powered "why this score?" generator
==========================================================
Given a transcript and the system's final risk score, produces a short list
of plain-English reasons that justify the score. The reasons are designed
to be displayed on the caregiver dashboard so a non-technical user can
understand at a glance *why* the AI flagged or cleared the message.

Cheap and fast:
  - Single Groq call with `response_format=json_object` for reliability.
  - For very low scores (< 25), we skip Groq entirely and synthesize a
    reassuring local explanation, saving tokens + latency.
  - Falls back gracefully when GROQ_API_KEY is missing or the call fails;
    in that case we still return useful reasons built from the upstream
    LLM signals (Bedrock / DashScope / Groq Llama).
"""

from __future__ import annotations

import json
import os
from typing import Iterable, List, Optional

import httpx
import structlog

logger = structlog.get_logger("fakeout.risk_explainer")

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

_SYSTEM_PROMPT = """You are Fakeout's risk explainer.
Given a Malaysian text/voice-transcribed message and the final scam risk score
(0-100) computed by upstream AI, produce 3-5 short bullet reasons that justify
the score. Write each bullet for a non-technical caregiver:
  - 12-22 words per bullet
  - Plain English, no jargon, no markdown, no emojis
  - Cite concrete evidence from the message (phrases, tactics, numbers) when
    you can; otherwise describe the pattern (e.g. "creates urgency by
    threatening account suspension").
  - If score < 30 say what is NORMAL about the message; do not invent risks.
  - If score >= 70 the first bullet must name the scam type
    (authority impersonation, financial extraction, family emergency, parcel
    scam, investment scam, love scam, etc.).

Respond ONLY as valid JSON with this exact shape:
{
  "risk_reasons": ["reason 1", "reason 2", "reason 3"]
}"""


def _band(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def _local_low_risk_reasons(transcript: str, score: int) -> List[str]:
    """Synthesize benign-message reasons without calling Groq."""
    snippet = (transcript or "").strip().replace("\n", " ")
    if len(snippet) > 90:
        snippet = snippet[:87] + "..."
    return [
        f"Risk band: {_band(score)} ({score}/100). No scam patterns matched by AI engines.",
        "No authority impersonation, urgency, or money-extraction language detected.",
        f"Message reads as ordinary conversation: \"{snippet}\"" if snippet else "Message contains no suspicious content.",
    ]


def _factor_reasons(risk_factors: Iterable[dict]) -> List[str]:
    """Build a useful reason list directly from the existing LLM factors.

    Used as a fallback when the Groq explainer call fails. We mine the
    explanations + flagged phrases that AWS Bedrock / Alibaba DashScope /
    Groq Llama already produced upstream so we never return an empty list.
    """
    reasons: List[str] = []
    seen_explanations: set[str] = set()
    flagged: List[str] = []

    for f in risk_factors or []:
        if not isinstance(f, dict):
            continue
        cat = str(f.get("category", ""))
        provider = f.get("provider") or cat
        explanation = (f.get("description") or "").strip()
        if explanation and explanation not in seen_explanations:
            seen_explanations.add(explanation)
            scam_type = (f.get("scam_type") or "").replace("_", " ").strip()
            prefix = f"{provider}: " if provider else ""
            tag = f" [{scam_type}]" if scam_type and scam_type != "unknown" else ""
            reasons.append(f"{prefix}{explanation}{tag}")
        for phrase in (f.get("matches") or [])[:3]:
            if phrase and phrase not in flagged:
                flagged.append(phrase)
        if len(reasons) >= 4:
            break

    if flagged:
        joined = ", ".join(f'"{p}"' for p in flagged[:4])
        reasons.append(f"Flagged phrases in the message: {joined}.")

    return reasons[:5]


async def explain_risk(
    transcript: str,
    risk_score: int,
    *,
    scam_type: Optional[str] = None,
    flagged_phrases: Optional[List[str]] = None,
    risk_factors: Optional[List[dict]] = None,
    sender_phone: str = "unknown",
) -> List[str]:
    """Return a bullet-list of reasons explaining `risk_score` for `transcript`."""
    score = int(max(0, min(100, risk_score or 0)))
    transcript = (transcript or "").strip()

    # Cheap path: very low risk → skip Groq, synthesize locally.
    if score < 25 or not transcript:
        reasons = _local_low_risk_reasons(transcript, score)
        logger.info(
            "risk_explainer_local_low",
            score=score,
            sender=sender_phone,
            reasons=len(reasons),
        )
        return reasons

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key.startswith("REPLACE"):
        logger.warning(
            "risk_explainer_no_groq",
            reason="GROQ_API_KEY not configured; using factor fallback.",
        )
        return _factor_reasons(risk_factors or []) or _local_low_risk_reasons(transcript, score)

    # Build a compact context block for Groq using whatever upstream signals
    # are already available. Keeping this small keeps latency low.
    context_parts = [f"Final risk score: {score}/100 ({_band(score)})"]
    if scam_type and scam_type != "unknown":
        context_parts.append(f"Detected scam type: {scam_type}")
    if flagged_phrases:
        joined = ", ".join(f'"{p}"' for p in flagged_phrases[:5])
        context_parts.append(f"Phrases the upstream models flagged: {joined}")
    context_block = "\n".join(context_parts)

    user_message = (
        f"Caregiver phone: +{sender_phone}\n"
        f"{context_block}\n\n"
        "MESSAGE TRANSCRIPT:\n"
        "---\n"
        f"{transcript}\n"
        "---\n\n"
        "Produce JSON with the risk_reasons list now."
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(raw)

        reasons_raw = data.get("risk_reasons") or []
        reasons = [
            str(r).strip().lstrip("-•*").strip()
            for r in reasons_raw
            if isinstance(r, (str, int, float)) and str(r).strip()
        ][:5]

        if not reasons:
            raise ValueError("Groq returned empty risk_reasons list")

        logger.info(
            "risk_explainer_done",
            sender=sender_phone,
            score=score,
            reasons=len(reasons),
        )
        return reasons

    except json.JSONDecodeError as e:
        logger.error("risk_explainer_json_parse_error", error=str(e))
    except httpx.HTTPError as e:
        logger.error("risk_explainer_http_error", error=str(e))
    except Exception as e:  # noqa: BLE001 – never crash the analysis pipeline
        logger.error("risk_explainer_unexpected_error", error=str(e))

    # Fallback: use whatever upstream factors gave us.
    fallback = _factor_reasons(risk_factors or [])
    if fallback:
        return fallback
    return [
        f"Risk band: {_band(score)} ({score}/100).",
        "Detailed AI explanation temporarily unavailable; verify with caregiver before approving.",
    ]
