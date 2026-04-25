"""
HelloFin – FastAPI Application Entry Point
==========================================
RELOAD TRIGGER: 2026-04-26 01:05:00
"""

import os
import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Force load .env from current directory
load_dotenv(override=True)
print(f"SERVER STARTING | GROQ_KEY: {os.getenv('GROQ_API_KEY', '')[:10]}...{os.getenv('GROQ_API_KEY', '')[-4:]}")

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.routers import webhook, risk, tng, chat, audio_risk, telegram
from app.services.audit_logger import AuditLogger
from app.services.mock_redis import MockRedis
from app.routers.telegram import start_telegram_polling

load_dotenv()

# Structured logging setup
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("hellofin")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: init Redis connection pool, audit logger."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        # Attempt real Redis connection
        redis = aioredis.from_url(redis_url, decode_responses=True)
        # Ping to verify connection
        await asyncio.wait_for(redis.ping(), timeout=2.0)
        app.state.redis = redis
        logger.info("redis_connected", redis_url=redis_url)
    except Exception as e:
        # Fallback to In-Memory Mock
        logger.warn("redis_connection_failed", error=str(e), action="falling_back_to_mock_redis")
        app.state.redis = MockRedis()
        
    app.state.audit = AuditLogger()
    logger.info("hellofin_startup")
    
    async def polling_wrapper():
        while True:
            try:
                await start_telegram_polling(app)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("telegram_polling_crashed", error=str(e))
                await asyncio.sleep(5) # Wait before restart
                
    # Start Telegram Polling in background
    polling_task = asyncio.create_task(polling_wrapper())
    
    yield
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    await app.state.redis.close()
    logger.info("hellofin_shutdown")

# --- RESTART TRIGGER: 2026-04-25 15:12:00 ---
app = FastAPI(
    title="HelloFin – Voice Phishing Detection",
    description="Bank-grade voice phishing detection for TNG Digital FINHACK 2026",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=True,
)


# CORS – allow frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ────────────────────────────────────────────
# Audit Middleware – logs every request (SOC2)
# ────────────────────────────────────────────
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Log every HTTP request/response for SOC2 compliance."""
    request_id = str(uuid.uuid4())
    start = time.time()

    # Attach request ID for tracing
    request.state.request_id = request_id

    response: Response = await call_next(request)

    duration_ms = round((time.time() - start) * 1000, 2)

    logger.info(
        "http_request",
        request_id=request_id,
        method=request.method,
        path=str(request.url.path),
        query=str(request.url.query),
        status_code=response.status_code,
        duration_ms=duration_ms,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", ""),
    )

    if response.status_code == 404:
        logger.warn("http_404_not_found", path=str(request.url.path), method=request.method)

    response.headers["X-Request-ID"] = request_id
    return response


# ────────────────────────────────────────────
# Routers
# ────────────────────────────────────────────
app.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
app.include_router(risk.router, prefix="/risk", tags=["Risk Scoring"])
app.include_router(tng.router, tags=["TNG eWallet & Caregiver"])
app.include_router(chat.router, prefix="/chat", tags=["Chat Widget"])
app.include_router(audio_risk.router, prefix="/risk", tags=["Voice Risk Detection"])
app.include_router(telegram.router, prefix="/webhook/telegram", tags=["Telegram Webhook"])


# ────────────────────────────────────────────
# Health check
# ────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API docs."""
    return {"message": "HelloFin API is running. Visit /docs for documentation."}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Handle favicon requests to prevent 404s in browser."""
    return Response(content="", media_type="image/x-icon")


@app.get("/health", tags=["System"])
async def health_check():
    """Health endpoint for Docker and load balancer probes."""
    return {"status": "healthy", "service": "hellofin", "version": "1.0.0"}
