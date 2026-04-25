"""Smoke test: can we invoke Qwen via DashScope?"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv("backend/.env")
sys.path.insert(0, "backend")

from app.services.alibaba_qwen_analyzer import analyze_with_dashscope as analyze_with_qwen

async def main():
    sample = "我是警察,你的银行账户涉及洗钱案件,请立刻把钱转到安全账户,不要告诉任何人,否则马上抓你"
    print(f"Calling Alibaba DashScope Qwen-Turbo...")
    result = await analyze_with_qwen(sample, sender_phone="api_test")
    print(f"  status        : {result.get('status', 'unknown')}")
    print(f"  risk_score    : {result.get('risk_score')}")
    print(f"  scam_type     : {result.get('scam_type')}")
    print(f"  confidence    : {result.get('confidence')}")
    print(f"  language      : {result.get('language_detected')}")
    print(f"  explanation   : {(result.get('explanation') or '')[:140]}")
    print(f"  flagged       : {result.get('flagged_phrases', [])[:3]}")
    if result.get("status") == "ok":
        print()
        print("DashScope Qwen leg works.")
    else:
        print()
        print("DashScope skipped/failed. Check error above.")

asyncio.run(main())
