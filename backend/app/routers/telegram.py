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


def _clean_token(token: str) -> str:
    return token.strip().replace("\n", "").replace("\r", "")


def _risk_factor_label(risk_factors: list[dict]) -> str:
    if not risk_factors:
        return "Analysis"

    first_factor = risk_factors[0] or {}
    label = first_factor.get("category") or first_factor.get("factor") or "Analysis"
    return str(label).replace("_", " ").title()


def _build_analysis_payload(chat_id: int, content: str, result) -> dict:
    score = result.risk_score
    label = _risk_factor_label(result.risk_factors)
    structured_text = (
        f"🧾 HelloFin Analysis Result\n\n"
        f"Input:\n{content}\n\n"
        f"📊 Status: Processed Successfully\n\n"
        f"--- AI VERDICT ---\n"
        f"Risk Score: {score}/100\n"
        f"Type: {label}\n\n"
        f"This has been logged to your dashboard."
    )
    high_risk = score >= 50
    header = "🚨 HelloFin RISK ALERT!\n\n" if high_risk else "✅ Message Scanned.\n\n"

    return {
        "chat_id": chat_id,
        "txn_id": result.txn_id,
        "transcript": result.transcript,
        "translation": result.translation,
        "risk_score": score,
        "risk_factors": result.risk_factors,
        "status": result.status,
        "risk_level": "HIGH" if high_risk else "LOW",
        "analysis_text": structured_text,
        "reply_text": header + structured_text,
    }


async def _send_telegram_message(chat_id: str, text: str, bot_token: str):
    clean_token = _clean_token(bot_token)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TELEGRAM_API_URL}{clean_token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
        resp.raise_for_status()


async def _notify_caregiver_push(content: str, sender_phone: str, result, token: str):
    push_chat_id = os.getenv("TELEGRAM_PUSH_CHAT_ID", "").strip()
    if not push_chat_id or not _clean_token(token):
        return

    threshold = int(os.getenv("TELEGRAM_PUSH_THRESHOLD", "50"))
    if result.risk_score < threshold:
        return

    summary = (
        f"🚨 HelloFin Push Notification\n\n"
        f"Risk Score: {result.risk_score}/100\n"
        f"Type: {_risk_factor_label(result.risk_factors)}\n"
        f"Sender: {sender_phone}\n\n"
        f"{content[:350]}"
    )

    try:
        await _send_telegram_message(push_chat_id, summary, token)
    except Exception as e:
        logger.error("telegram_push_failed", error=str(e))

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

@router.get("/version")
async def get_version():
    return {"version": "V2.2", "status": "active"}

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Webhook endpoint for Telegram."""
    data = await request.json()
    await handle_telegram_update(data, request.app)
    return {"status": "ok"}


@router.post("/analyze")
async def telegram_analyze(request: Request):
    """n8n-facing Telegram analysis endpoint."""
    payload = await request.json()
    return await analyze_telegram_payload(payload, request.app)


async def analyze_telegram_payload(payload: dict, app) -> dict:
    redis = app.state.redis
    chat_id = payload.get("chat_id") or payload.get("sender_chat_id") or payload.get("message", {}).get("chat", {}).get("id")
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id is required")

    text = payload.get("text") or payload.get("message", {}).get("text") or payload.get("message", {}).get("caption")
    transcript = payload.get("transcript") or text
    if not transcript:
        raise HTTPException(status_code=400, detail="text or transcript is required")

    sender_phone = payload.get("sender_phone") or f"tg_{chat_id}"
    transaction_amount = float(payload.get("transaction_amount", 0.0) or 0.0)
    is_new_payee = bool(payload.get("is_new_payee", False))
    message_type = payload.get("message_type") or "telegram_text"

    result = await process_message(
        redis=redis,
        transcript=transcript,
        sender_phone=sender_phone,
        is_new_payee=is_new_payee,
        transaction_amount=transaction_amount,
        message_type=message_type,
    )

    await _notify_caregiver_push(transcript, sender_phone, result, os.getenv("TELEGRAM_BOT_TOKEN", ""))
    response = _build_analysis_payload(chat_id, transcript, result)
    response["bot_token_configured"] = bool(_clean_token(os.getenv("TELEGRAM_BOT_TOKEN", "")))
    return response


async def handle_telegram_update(update: dict, app):
    """Shared logic for both webhook and polling."""
    raw_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    token = _clean_token(raw_token)
    
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
        transcript = None
        if voice:
            # Handle Voice
            file_id = voice.get("file_id")
            # 1. Download
            local_path = await download_telegram_file(file_id, token)
            # 2. Transcribe
            transcript = await transcribe_audio(local_path)
            print(f"[DEBUG] VOICE TRANSCRIPT: {transcript}")
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
            print(f"[DEBUG] TEXT MESSAGE: {text}")
            result = await process_message(
                redis=redis,
                transcript=text,
                sender_phone=f"tg_{chat_id}",
                message_type="telegram_text",
                transaction_amount=0.0
            )
        else:
            return

        msg_content = transcript if voice else text
        response = _build_analysis_payload(chat_id, msg_content, result)
        await _notify_caregiver_push(msg_content, f"tg_{chat_id}", result, token)
        await send_telegram_reply(chat_id, response["reply_text"], token)

    except Exception as e:
        logger.error("telegram_handle_error", error=str(e))
        # Send error to chat for debugging
        await send_telegram_reply(chat_id, f"❌ Error processing message: {str(e)[:100]}", token)


async def start_telegram_polling(app):
    """Background task to poll for Telegram updates (no ngrok required)."""
    raw_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    token = raw_token.strip().replace("\n", "").replace("\r", "")
    
    if not token or "REPLACE" in token:
        print("[DEBUG] Telegram Token is MISSING or default. Check .env!")
        return

    # 1. Verify Connection with getMe
    print(f"[DEBUG] Testing connection to Telegram for Bot Token: {token[:10]}...")
    try:
        async with httpx.AsyncClient() as client:
            test_resp = await client.get(f"{TELEGRAM_API_URL}{token}/getMe")
            if test_resp.status_code == 200:
                bot_info = test_resp.json()
                bot_name = bot_info["result"]["first_name"]
                print(f"[DEBUG] SUCCESS: Connected to Telegram Bot: @{bot_info['result']['username']} ({bot_name})")
            else:
                print(f"[DEBUG] FAILED: Telegram API returned {test_resp.status_code}. Your token might be wrong.")
                return

            # 2. Clear any existing webhook
            print("[DEBUG] Clearing old Webhooks to enable polling...")
            await client.get(f"{TELEGRAM_API_URL}{token}/deleteWebhook")
    except Exception as e:
        print(f"[DEBUG] FAILED to connect to Telegram: {e}")
        return

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    offset = 0
    print("[DEBUG] Bot is now LISTENING for messages...")

    while True:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {
                    "offset": offset,
                    "timeout": 0,  # Short poll - doesn't block the event loop
                    "allowed_updates": ["message"]
                }
                resp = await client.get(url, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("result", [])
                    if results:
                        print(f"[DEBUG] RECEIVED {len(results)} NEW MESSAGES!")
                        
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
            
            # Sleep between polls to not hammer the API and free the event loop
            await asyncio.sleep(1.5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("telegram_polling_error", error=str(e))
            await asyncio.sleep(5)


async def send_telegram_reply(chat_id: int, text: str, bot_token: str):
    """Send a message back to the Telegram chat."""
    clean_token = bot_token.strip().replace("\n", "").replace("\r", "")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{TELEGRAM_API_URL}{clean_token}/sendMessage",
                json={"chat_id": chat_id, "text": text}
            )
            if resp.status_code != 200:
                print(f"[DEBUG] ❌ Telegram Reply FAILED: {resp.status_code} - {resp.text}")
            resp.raise_for_status()
        except Exception as e:
            logger.error("telegram_reply_failed", error=str(e))
