"""Smoke test: can we invoke Claude 3 Haiku via AWS Bedrock?"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv("backend/.env")
sys.path.insert(0, "backend")

from app.services.aws_bedrock_analyzer import analyze_with_bedrock

async def main():
    sample = "This is PDRM. Your account is under investigation. Transfer to safe account immediately or face arrest."
    print(f"Calling AWS Bedrock Claude 3 Haiku in {os.getenv('AWS_BEDROCK_REGION')}...")
    result = await analyze_with_bedrock(sample, sender_phone="api_test")
    print(f"  status        : {result.get('status', 'unknown')}")
    print(f"  risk_score    : {result.get('risk_score')}")
    print(f"  scam_type     : {result.get('scam_type')}")
    print(f"  confidence    : {result.get('confidence')}")
    print(f"  language      : {result.get('language_detected')}")
    print(f"  explanation   : {result.get('explanation', '')[:140]}")
    print(f"  flagged       : {result.get('flagged_phrases', [])[:3]}")
    if result.get("status") == "ok":
        print()
        print("Bedrock leg works.")
    else:
        print()
        print("Bedrock skipped/failed. Check error in logs above.")

asyncio.run(main())
