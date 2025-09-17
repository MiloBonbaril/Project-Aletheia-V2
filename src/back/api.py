# api.py
# FastAPI application for Ollama model interactions with observability and shared middleware
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from internal_clients import InternalClients, create_internal_clients, shutdown_clients
from observability import RequestContextMiddleware, configure_logging
from timeout import RequestTimeoutMiddleware
from ollama_interface.client import OllamaClient


configure_logging()
logger = logging.getLogger("api.app")
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


def _allowed_origins() -> List[str]:
    raw = os.getenv("BACK_ALLOWED_ORIGINS", "")
    if raw:
        origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
        if origins:
            return origins
    return ["http://localhost:3000"]


def _request_timeout_seconds() -> int:
    try:
        return int(os.getenv("BACK_REQUEST_TIMEOUT", "15"))
    except ValueError:
        return 15


def _http_client_timeout() -> float:
    try:
        return float(os.getenv("BACK_HTTP_TIMEOUT", "10"))
    except ValueError:
        return 10.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API startup")
    clients = create_internal_clients(
        ollama_url=os.getenv("OLLAMA_API_URL"),
        http_timeout=_http_client_timeout(),
    )
    app.state.clients = clients

    try:
        yield
    finally:
        await shutdown_clients(clients)
        logger.info("API shutdown complete")


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(
        "Rate limit exceeded",
        extra={
            "path": request.url.path,
            "client_host": request.client.host if request.client else None,
        },
    )

    reset = getattr(exc, "reset", None)
    headers: Dict[str, str] = {}
    if isinstance(reset, (int, float)):
        headers["Retry-After"] = str(int(reset))

    return JSONResponse(status_code=429, content={"detail": "Too many requests"}, headers=headers)


# Middleware order: request context last wraps entire stack for logging
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestTimeoutMiddleware, timeout=_request_timeout_seconds())
app.add_middleware(RequestContextMiddleware)


class PullModelRequest(BaseModel):
    model_name: str


class WarmModelRequest(BaseModel):
    model_name: str


class ChatRequest(BaseModel):
    model_name: str
    messages: List[Dict[str, str]]
    options: Optional[Dict[str, Any]] = None


def get_clients(request: Request) -> InternalClients:
    return request.app.state.clients


def get_ollama_client(clients: InternalClients = Depends(get_clients)) -> OllamaClient:
    return clients.ollama


@app.get("/models")
@limiter.limit("60/minute")
async def list_models(
    request: Request,
    ollama: OllamaClient = Depends(get_ollama_client),
):
    return await run_in_threadpool(ollama.list_models)


@app.post("/models/pull")
@limiter.limit("30/minute")
async def pull_model(
    request: Request,
    req: PullModelRequest,
    ollama: OllamaClient = Depends(get_ollama_client),
):
    try:
        await run_in_threadpool(ollama.pull_model, req.model_name)
        return {"status": "success"}
    except Exception as exc:
        logger.exception("Failed to pull model", extra={"model_name": req.model_name})
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/models/warm")
@limiter.limit("30/minute")
async def warm_model(
    request: Request,
    req: WarmModelRequest,
    ollama: OllamaClient = Depends(get_ollama_client),
):
    try:
        result = await run_in_threadpool(ollama.warm_model, req.model_name)
        return {"status": "success", "result": result}
    except Exception as exc:
        logger.exception("Failed to warm model", extra={"model_name": req.model_name})
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/chat")
@limiter.limit("120/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    ollama: OllamaClient = Depends(get_ollama_client),
):
    try:
        response = await run_in_threadpool(
            ollama.chat,
            req.model_name,
            req.messages,
            req.options,
        )
        return {"message": response.message.content}
    except Exception as exc:
        logger.exception("Chat request failed", extra={"model_name": req.model_name})
        raise HTTPException(status_code=400, detail=str(exc)) from exc

