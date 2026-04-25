import os
import re
import json
import httpx
import structlog
from app.services.huggingface_client import translate_text_hf

logger = structlog.get_logger("fakeout.translation")

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = "You are a translation assistant. Translate the given text to English, preserving meaning, tone, and any technical terms. Respond with ONLY the translated text, no extra formatting."

# ---------------------------------------------------------------------------
# Lightweight language detection (no extra dependencies)
# Goal: decide whether `text` is *already English* so we can skip the LLM
# translator. The LLM translator otherwise paraphrases English input
# ("rosak" -> "damaged", "I am a police officer" -> reworded), polluting the
# alert's translation field with a mangled version of the original.
# ---------------------------------------------------------------------------

# Words that almost only appear in Bahasa Malaysia / Indonesian text. If any
# of these occur and no English-only marker words are present, treat as non-EN.
_BAHASA_MARKERS = {
    "anda", "akaun", "saya", "kami", "kita", "mereka", "ialah", "adalah",
    "ini", "itu", "dengan", "kepada", "daripada", "sila", "jangan", "tidak",
    "bukan", "akan", "sekarang", "boleh", "tolong", "wang", "polis", "polisi",
    "pegawai", "bekukan", "dibekukan", "pengesahan", "pengesah", "rosak",
    "sesiapa", "semua", "lah", "yang", "untuk", "dalam", "sudah", "belum",
    "bahawa", "tetapi", "kerana", "supaya", "berikan", "berikut", "negara",
    "kastam", "amaran", "darurat", "segera", "perhatian",
}

# Common English-only function/marker words. Several of these in the text is a
# strong signal it is English (works even for Manglish that mixes a Malay word
# or two like "rosak").
_ENGLISH_MARKERS = {
    "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "can", "could", "should", "may", "might", "must",
    "you", "your", "yours", "youre", "i", "me", "my", "mine",
    "we", "our", "they", "their", "he", "she", "his", "her",
    "this", "that", "these", "those", "there", "here",
    "and", "or", "but", "if", "because", "so", "than", "then",
    "to", "of", "in", "on", "at", "for", "with", "from", "into",
    "not", "no", "yes", "please", "thanks", "thank",
    "account", "transfer", "money", "bank", "code", "verify",
    "verification", "now", "tonight", "today", "tomorrow",
    "emergency", "urgent", "investigation", "police", "officer",
    "warrant", "arrest", "frozen", "freeze",
}

# Token splitter: keep only ASCII letters/digits, drop punctuation, lowercase.
_TOKEN_RE = re.compile(r"[A-Za-z']+")


def is_english(text: str) -> bool:
    """Return True if `text` is already in English.

    Heuristic, no external models:
      1. If the text contains a meaningful amount of non-ASCII letters
         (Chinese, Arabic, Tamil, etc.) -> NOT English.
      2. Otherwise tokenize and compare counts of English-only marker words
         vs Bahasa-only marker words. English wins on tie or absence of both
         (so plain "Hi mum, dinner at 7pm tonight" is treated as English).
    """
    if not text or not text.strip():
        return True  # empty -> nothing to translate

    # 1. Non-ASCII letters threshold. Allow a handful (emoji, accents) but
    #    treat large blocks of CJK / Arabic / Tamil as non-English.
    non_ascii_letters = sum(
        1 for ch in text if ch.isalpha() and ord(ch) > 127
    )
    total_letters = sum(1 for ch in text if ch.isalpha()) or 1
    if non_ascii_letters / total_letters > 0.15:
        return False

    # 2. Marker-word vote on the lowercased ASCII tokens.
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    if not tokens:
        return True  # only digits/punctuation -> safe to skip translation

    en_hits = sum(1 for t in tokens if t in _ENGLISH_MARKERS)
    bm_hits = sum(1 for t in tokens if t in _BAHASA_MARKERS)

    # Strong Bahasa signal beats weak English signal.
    if bm_hits >= 2 and bm_hits >= en_hits:
        return False
    if bm_hits >= 1 and en_hits == 0:
        return False
    return True


async def translate_text(text: str, target_language: str = "English") -> str:
    """Translate input text to the target language.

    If the source is already in the target language (English by default), we
    return an empty string so callers know to keep the original transcript
    verbatim rather than waste an LLM call paraphrasing it.

    Args:
        text: Source text (any language).
        target_language: Language to translate into (default English).
    Returns:
        Translated text string, or "" when no translation is needed/possible.
    """
    # Short-circuit: don't translate English -> English. This is the bug the
    # Telegram bot was hitting where an English voice transcript was being
    # re-paraphrased and stored as a fake "translation".
    if target_language.strip().lower().startswith("english") and is_english(text):
        logger.info(
            "translation_skipped_already_english",
            text_len=len(text or ""),
        )
        return ""

    # Try HuggingFace first if key is available
    hf_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    if hf_key and not hf_key.startswith("REPLACE"):
        hf_translation = await translate_text_hf(text, target_language)
        if hf_translation:
            return hf_translation

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key.startswith("REPLACE"):
        logger.warning("translate_skipped", reason="GROQ_API_KEY not configured")
        return ""
    user_message = f"Translate the following text to {target_language}:\n\n---\n{text}\n---\n"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
        translation = resp.json()["choices"][0]["message"]["content"].strip()
        logger.info("translation_done", original_len=len(text), translated_len=len(translation))
        return translation
    except Exception as e:
        logger.error("translation_error", error=str(e))
        return ""
