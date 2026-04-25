import os
import asyncio
from dotenv import load_dotenv
import httpx

load_dotenv()

async def test():
    print("Testing GROQ JSON format...")
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": "You output JSON."}, {"role": "user", "content": "Output JSON"}],
                "response_format": {"type": "json_object"}
            }
        )
        print(f"Groq Status: {resp.status_code}")
        print(resp.text)

if __name__ == "__main__":
    asyncio.run(test())
