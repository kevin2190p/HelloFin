import os, json
import httpx
import structlog

logger = structlog.get_logger("hellofin.gemini")

async def analyze_risk_with_gemini(text: str, sender_phone: str = "unknown") -> dict:
    """
    Perform deep scam detection using Gemini 1.5 Flash.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"risk_score": 0, "is_scam": False}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    You are an elite voice phishing detection AI. Analyze this message from {sender_phone}:
    "{text}"

    Detect: authority impersonation, urgency, financial extraction, family emergencies, or investment scams.
    
    Respond ONLY with valid JSON:
    {{
      "is_scam": true/false,
      "risk_score": 0-100,
      "scam_type": "string",
      "explanation": "concise explanation",
      "confidence": 0-100,
      "detected_tactics": ["list"]
    }}
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(raw_text)
    except Exception as e:
        logger.error("gemini_risk_analysis_failed", error=str(e))
        return {"risk_score": 0, "is_scam": False, "explanation": "Gemini analysis failed."}

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
