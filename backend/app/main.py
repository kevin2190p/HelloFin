"""
HelloFin – FastAPI Application Entry Point
==========================================
Bank-grade voice phishing detection API.
SOC2-ready audit logging, zero-trust design.
"""

import os
import time
import uuid
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.routers import webhook, risk, tng, chat
from app.services.audit_logger import AuditLogger

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
    app.state.redis = aioredis.from_url(redis_url, decode_responses=True)
    app.state.audit = AuditLogger()
    logger.info("hellofin_startup", redis_url=redis_url)
    yield
    await app.state.redis.close()
    logger.info("hellofin_shutdown")


app = FastAPI(
    title="HelloFin – Voice Phishing Detection",
    description="Bank-grade voice phishing detection for TNG Digital FINHACK 2026",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS – allow frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

    response.headers["X-Request-ID"] = request_id
    return response


# ────────────────────────────────────────────
# Routers
# ────────────────────────────────────────────
app.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
app.include_router(risk.router, prefix="/risk", tags=["Risk Scoring"])
app.include_router(tng.router, tags=["TNG eWallet & Caregiver"])
app.include_router(chat.router, prefix="/chat", tags=["Chat Widget"])


# ────────────────────────────────────────────
# Health check
# ────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Health endpoint for Docker and load balancer probes."""
    return {"status": "healthy", "service": "hellofin", "version": "1.0.0"}
