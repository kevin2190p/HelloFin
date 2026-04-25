import os
import uuid
import time
import asyncio
from pathlib import Path
import httpx
import structlog
from fastapi import APIRouter, Request, HTTPException
from app.services.whisper_client import transcribe_audio
from app.services.analysis_service import process_message

logger = structlog.get_logger("hellofin.telegram")

router = APIRouter()

AUDIO_DIR = Path("audios/telegram")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

TELEGRAM_API_URL = "https://api.telegram.org/bot"

async def download_telegram_file(file_id: str, bot_token: str) -> str:
    """Download a file from Telegram and return the local path."""
    async with httpx.AsyncClient() as client:
        # 1. Get file path
        resp = await client.get(f"{TELEGRAM_API_URL}{bot_token}/getFile", params={"file_id": file_id})
        resp.raise_for_status()
        file_path_tg = resp.json()["result"]["file_path"]
        
        # 2. Download file
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path_tg}"
        file_ext = Path(file_path_tg).suffix
        local_filename = f"{uuid.uuid4()}{file_ext}"
        local_path = AUDIO_DIR / local_filename
        
        file_resp = await client.get(download_url)
        file_resp.raise_for_status()
        
        with open(local_path, "wb") as f:
            f.write(file_resp.content)
            
        return str(local_path)

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Webhook endpoint for Telegram."""
    data = await request.json()
    await handle_telegram_update(data, request.app)
    return {"status": "ok"}


async def handle_telegram_update(update: dict, app):
    """Shared logic for both webhook and polling."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or "REPLACE" in token:
        logger.error("telegram_handle_error", detail="TELEGRAM_BOT_TOKEN is missing or invalid in .env")
        return

    redis = app.state.redis
    
    # Check for message or voice
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text")
    voice = message.get("voice") or message.get("audio")

    if not chat_id:
        return

    logger.info("telegram_update_received", chat_id=chat_id, has_text=bool(text), has_voice=bool(voice))

    try:
        if voice:
            # Handle Voice
            file_id = voice.get("file_id")
            # 1. Download
            local_path = await download_telegram_file(file_id, token)
            # 2. Transcribe
            transcript = await transcribe_audio(local_path)
            # 3. Analyze
            result = await process_message(
                redis=redis,
                transcript=transcript,
                sender_phone=f"tg_{chat_id}",
                message_type="telegram_voice",
                transaction_amount=round(float(time.time() % 1000) + 500, 2)
            )
            # Cleanup
            if os.path.exists(local_path):
                os.remove(local_path)
        elif text:
            # Handle Text
            result = await process_message(
                redis=redis,
                transcript=text,
                sender_phone=f"tg_{chat_id}",
                message_type="telegram_text",
                transaction_amount=0.0
            )
        else:
            return

        # Always reply with the score so the user can see real data
        score = result.risk_score
        if score >= 50:
            warning = f"🚨 HelloFin RISK ALERT!\n\nRisk Score: {score}/100\nType: {result.risk_factors[0]['category'].replace('_', ' ').title() if result.risk_factors else 'Suspicious'}\n\nThis message has been flagged on your Caregiver Dashboard."
            await send_telegram_reply(chat_id, warning, token)
        else:
            await send_telegram_reply(chat_id, f"✅ Message scanned. Risk is LOW ({score}/100). Stay safe!", token)

    except Exception as e:
        logger.error("telegram_handle_error", error=str(e))
        # Send error to chat for debugging
        await send_telegram_reply(chat_id, f"❌ Error processing message: {str(e)[:100]}", token)


async def start_telegram_polling(app):
    """Background task to poll for Telegram updates (no ngrok required)."""
    raw_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    token = raw_token.strip().replace("\n", "").replace("\r", "")
    
    if not token or "REPLACE" in token:
        print("[DEBUG] ❌ Telegram Token is MISSING or default. Check .env!")
        return

    # 1. Verify Connection with getMe
    print(f"[DEBUG] 🔍 Testing connection to Telegram for Bot Token: {token[:10]}...")
    try:
        async with httpx.AsyncClient() as client:
            test_resp = await client.get(f"{TELEGRAM_API_URL}{token}/getMe")
            if test_resp.status_code == 200:
                bot_info = test_resp.json()
                bot_name = bot_info["result"]["first_name"]
                print(f"[DEBUG] ✅ SUCCESS: Connected to Telegram Bot: @{bot_info['result']['username']} ({bot_name})")
            else:
                print(f"[DEBUG] ❌ FAILED: Telegram API returned {test_resp.status_code}. Your token might be wrong.")
                return

            # 2. Clear any existing webhook
            print("[DEBUG] 🧹 Clearing old Webhooks to enable polling...")
            await client.get(f"{TELEGRAM_API_URL}{token}/deleteWebhook")
    except Exception as e:
        print(f"[DEBUG] ❌ FAILED to connect to Telegram: {e}")
        return

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    offset = 0
    print("[DEBUG] 👂 Bot is now LISTENING for messages...")

    while True:
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "offset": offset,
                    "timeout": 5, # Faster response
                    "allowed_updates": ["message"]
                }
                # print(f"[DEBUG] Polling Telegram for updates (offset={offset})...")
                resp = await client.get(url, params=params, timeout=10.0)
                
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("result", [])
                    if results:
                        print(f"[DEBUG] 🔥 RECEIVED {len(results)} NEW MESSAGES!")
                    else:
                        # Minimal heartbeat
                        pass
                        
                    for update in results:
                        offset = update["update_id"] + 1
                        asyncio.create_task(handle_telegram_update(update, app))
                elif resp.status_code == 409:
                    print("[DEBUG] Conflict detected. Webhook active. Clearing...")
                    logger.warn("telegram_polling_conflict", detail="Webhook active. Trying to clear...")
                    await client.get(f"{TELEGRAM_API_URL}{token}/deleteWebhook")
                else:
                    print(f"[DEBUG] Telegram Polling error: {resp.status_code}")
                    logger.error("telegram_polling_error", status=resp.status_code)
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("telegram_polling_error", error=str(e))
            await asyncio.sleep(5)


async def send_telegram_reply(chat_id: int, text: str, bot_token: str):
    """Send a message back to the Telegram chat."""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{TELEGRAM_API_URL}{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text}
            )
        except Exception as e:
            logger.error("telegram_reply_failed", error=str(e))
