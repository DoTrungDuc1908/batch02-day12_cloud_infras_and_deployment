"""
Production AI Agent for Day 12.

It demonstrates 12-factor config, JSON logs, API-key auth, Redis-backed
rate limiting, monthly budget protection, health/readiness probes, graceful
shutdown, and stateless conversation history.
"""
import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_and_record_budget, estimate_cost
from app.rate_limiter import check_rate_limit
from app.redis_store import ping_redis, redis_client
from app.mock_llm import ask as llm_ask


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    handlers=[handler],
    force=True,
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
IS_READY = False
REQUEST_COUNT = 0
ERROR_COUNT = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global IS_READY
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))
    IS_READY = True
    logger.info(json.dumps({"event": "ready"}))
    try:
        yield
    finally:
        IS_READY = False
        redis_client.close()
        logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global REQUEST_COUNT, ERROR_COUNT
    started = time.time()
    REQUEST_COUNT += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if "server" in response.headers:
            del response.headers["server"]
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((time.time() - started) * 1000, 1),
        }))
        return response
    except Exception:
        ERROR_COUNT += 1
        logger.exception("request_failed")
        raise


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field("default-user", min_length=1, max_length=80)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    history_length: int
    budget_used_usd: float
    timestamp: str


def _history_key(user_id: str) -> str:
    return f"history:{user_id}"


def _load_history(user_id: str) -> list[str]:
    return redis_client.lrange(_history_key(user_id), 0, settings.history_limit - 1)


def _save_exchange(user_id: str, question: str, answer: str) -> int:
    key = _history_key(user_id)
    entry = json.dumps(
        {
            "question": question,
            "answer": answer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
    )
    pipe = redis_client.pipeline()
    pipe.lpush(key, entry)
    pipe.ltrim(key, 0, settings.history_limit - 1)
    pipe.expire(key, 30 * 24 * 3600)
    pipe.llen(key)
    *_, history_length = pipe.execute()
    return int(history_length)


def _build_prompt(question: str, history: list[str]) -> str:
    if not history:
        return question
    recent = []
    for raw in reversed(history[:4]):
        try:
            item = json.loads(raw)
            recent.append(f"User: {item['question']}\nAgent: {item['answer']}")
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return "\n".join(recent + [f"User: {question}", "Agent:"])


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
            "metrics": "GET /metrics (requires X-API-Key)",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _authenticated_user: str = Depends(verify_api_key),
):
    check_rate_limit(body.user_id)

    history = _load_history(body.user_id)
    prompt = _build_prompt(body.question, history)
    input_tokens = max(1, len(prompt.split()) * 2)

    logger.info(json.dumps({
        "event": "agent_call",
        "user_id": body.user_id,
        "question_chars": len(body.question),
        "history_items": len(history),
        "client": request.client.host if request.client else "unknown",
    }))

    answer = llm_ask(prompt)
    output_tokens = max(1, len(answer.split()) * 2)
    cost = estimate_cost(input_tokens, output_tokens)
    budget_used = check_and_record_budget(body.user_id, cost)
    history_length = _save_exchange(body.user_id, body.question, answer)

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        history_length=history_length,
        budget_used_usd=round(budget_used, 6),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health", tags=["Operations"])
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": REQUEST_COUNT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    if not IS_READY:
        raise HTTPException(status_code=503, detail="Not ready")
    try:
        ping_redis()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis not ready: {exc}") from exc
    return {"ready": True, "redis": "ok"}


@app.get("/metrics", tags=["Operations"])
def metrics(_authenticated_user: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": REQUEST_COUNT,
        "error_count": ERROR_COUNT,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "monthly_budget_usd": settings.monthly_budget_usd,
    }


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "SIGTERM", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
