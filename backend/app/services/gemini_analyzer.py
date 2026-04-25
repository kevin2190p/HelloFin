import os
import httpx
import structlog

logger = structlog.get_logger("hellofin.gemini")

async def get_gemini_explanation(transcript: str, risk_score: int) -> str:
    """
    Calls Google Gemini API to generate a logical explanation for the risk score.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("gemini_api_key_missing")
        return "Gemini API key is not configured."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    Analyze the following transcript from a potential scam call/message and the assigned risk score.
    Provide a logical, concise explanation (1-2 sentences) of why the risk is { 'high' if risk_score >= 50 else 'low' } based on the content.
    
    Transcript: "{transcript}"
    Risk Score: {risk_score}/100
    
    Explanation:
    """

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Extract text from Gemini response
            explanation = data['candidates'][0]['content']['parts'][0]['text'].strip()
            return explanation
    except Exception as e:
        logger.error("gemini_api_failed", error=str(e))
        return f"Could not generate AI explanation at this time. (Risk Score: {risk_score})"
