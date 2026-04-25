import os
import httpx
import structlog

logger = structlog.get_logger("hellofin.huggingface")

async def translate_text_hf(text: str, target_language: str = "English") -> str:
    """
    Translate text using Hugging Face Inference API.
    """
    api_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    if not api_key or "REPLACE" in api_key:
        return ""

    # Model for multilingual translation
    API_URL = "https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-mul-en"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                API_URL,
                headers=headers,
                json={"inputs": text}
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("translation_text", "")
            
            return ""
    except Exception as e:
        logger.error("hf_translation_error", error=str(e))
        return ""

async def get_scam_probability(text: str) -> float:
    """
    Use HuggingFace Zero-Shot Classification to get a scam probability.
    """
    api_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    if not api_key or "REPLACE" in api_key:
        return 0.0

    API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
    headers = {"Authorization": f"Bearer {api_key}"}

    payload = {
        "inputs": text,
        "parameters": {"candidate_labels": ["scam", "phishing", "fraud", "legitimate", "normal message"]}
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(API_URL, headers=headers, json=payload)
            if resp.status_code == 200:
                result = resp.json()
                labels = result.get("labels", [])
                scores = result.get("scores", [])
                
                scam_score = 0.0
                for label, score in zip(labels, scores):
                    if label in ["scam", "phishing", "fraud"]:
                        scam_score = max(scam_score, score)
                
                return scam_score
    except Exception as e:
        logger.error("hf_classification_error", error=str(e))
    
    return 0.0
