from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth, calendar, companies, comparisons, dcf, health, market, news, peers
from app.api.routers import quote as quote_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger, request_id_ctx
from app.api.routers import watchlist
from app.lifespan import lifespan

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("investify.api")

app = FastAPI(
    title="Investify API",
    description="BIST Investment Intelligence Platform — Phase 1 backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    token = request_id_ctx.set(request_id)
    start = time.monotonic()
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    latency_ms = (time.monotonic() - start) * 1000
    logger.info(
        "request_completed",
        extra={
            "requestId": request_id,
            "method": request.method,
            "path": request.url.path,
            "latencyMs": round(latency_ms, 2),
        },
    )
    response.headers["x-request-id"] = request_id
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(dcf.router)
app.include_router(peers.router)
app.include_router(comparisons.router)
app.include_router(news.router)
app.include_router(market.router)
app.include_router(calendar.router)
app.include_router(quote_router.router)
app.include_router(watchlist.router)
