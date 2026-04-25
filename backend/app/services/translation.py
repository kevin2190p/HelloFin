import os
import json
import httpx
import structlog
from app.services.huggingface_client import translate_text_hf

logger = structlog.get_logger("hellofin.translation")

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = "You are a translation assistant. Translate the given text to English, preserving meaning, tone, and any technical terms. Respond with ONLY the translated text, no extra formatting."

async def translate_text(text: str, target_language: str = "English") -> str:
    """Translate input text to the target language using Groq LLM.
    Args:
        text: Source text (any language).
        target_language: Language to translate into (default English).
    Returns:
        Translated text string.
    """
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
